"""Compatibility adapter for the existing child-agent creation and group format."""
import json
import re
import threading
import uuid
import shutil
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app import user_app as legacy
from app import experience_runtime as runtime

router = APIRouter(prefix='/user/children', dependencies=[Depends(runtime.guard)])
CREATE_LOCK = threading.Lock()
logger = logging.getLogger(__name__)

def create_octopus_child(request, parent):
    child_id=parent.name+'_sub_'+uuid.uuid4().hex[:12]
    root=runtime.AGENTS/child_id
    source=runtime.ROOT/'agent_provider/octopus'
    shutil.copytree(source,root/'octopus_build',ignore=shutil.ignore_patterns(
        '.venv','.web-venv','venv','.git','__pycache__','.env','*.log','*.egg-info'))
    values,_=runtime.model_env(parent)
    inherited={k:v for k,v in values.items() if k in {'OPENAI_API_KEY','OPENAI_BASE_URL','OPENAI_MODEL','MODEL_PROVIDER'}}
    (root/'octopus_build/.env').write_text(''.join(f'{k}={v}\n' for k,v in inherited.items()),encoding='utf-8')
    manifest={'id':child_id,'name':request.name.strip(),'description':request.description,
              'agent_type':'octopus','parent_phc_id':request.parent_phc_id,
              'binding':{'PHC_id':request.parent_phc_id},'credential_mode':'inherited_from_parent',
              'capabilities':request.capabilities}
    (root/'agent_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    mapping={'text-processing':'text_processor','news-search':'news','web-browsing':'web_browsing'}
    (root/'active_agents.json').write_text(json.dumps({'allowed_agents':[mapping[c] for c in request.capabilities if c in mapping],'theme':'default'}),encoding='utf-8')
    child=legacy.SubAgentInfo(id=child_id,name=request.name.strip(),phc_id=child_id,status='created',
          created_at=datetime.now(timezone.utc).isoformat(),deploy_path=str(root))
    groups=legacy.list_agent_groups(request.parent_phc_id)
    group=groups[0] if groups else legacy.MultiAgentGroup(group_id='group_'+request.parent_phc_id,
          group_name='Octopus companions',parent_agent_id=request.parent_phc_id,sub_agents=[],
          communication_config={'protocol':'ANP','scope':'local'},created_at=child.created_at)
    group.sub_agents.append(child);legacy.save_agent_group(group)
    return {'success':True,'child':{'id':child.id,'phc_id':child.phc_id,'name':child.name}}

def create_openclaw_branch(request, parent):
    """Create a local execution branch, not a newly issued identity credential."""
    from agent_provider.openclaw.openclaw_package import build_openclaw_agent_files
    import hashlib
    child_id = parent.name + '_exec_' + uuid.uuid4().hex[:12]
    root = runtime.AGENTS / child_id
    root.mkdir(parents=True, exist_ok=False)
    values, _ = runtime.model_env(parent)
    model = values.get('OPENAI_MODEL') or values.get('OPENCLAW_MODEL') or 'deepseek-v4-pro'
    config = {'provider': values.get('LLM_PROVIDER', 'openai'), 'model': model,
              'base_url': values.get('OPENAI_BASE_URL', '')}
    cmc = legacy.build_sub_agent_cmc(request.capabilities, config)
    build_openclaw_agent_files(root=str(root), phc={'id': request.parent_phc_id}, pa={},
        cmc=cmc, hid=hashlib.sha256(child_id.encode()).hexdigest(),
        hooks_config={}, skills_config=[], llm_config=config)
    manifest = {'id': child_id, 'name': request.name.strip(), 'description': request.description,
        'agent_type': 'openclaw', 'role': 'executor', 'parent_phc_id': request.parent_phc_id,
        'binding': {'PHC_id': request.parent_phc_id}, 'credential_mode': 'inherited_from_parent',
        'capabilities': request.capabilities}
    (root / 'agent_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    binding_path = root / 'openclaw_package/openclaw_binding.json'
    binding = json.loads(binding_path.read_text(encoding='utf-8'))
    binding.update(instance_id=child_id, credential_mode='inherited_from_parent',
                   note='Local execution branch linked to parent identity; no separate PHC issued.')
    binding_path.write_text(json.dumps(binding, ensure_ascii=False, indent=2), encoding='utf-8')
    # Keys stay on the server. Runtime resolves the parent's model configuration.
    (root / 'openclaw_package/.env').write_text('', encoding='utf-8')
    child = legacy.SubAgentInfo(id=child_id, name=request.name.strip(), phc_id=child_id,
        status='created', created_at=datetime.now(timezone.utc).isoformat(), deploy_path=str(root))
    groups = legacy.list_agent_groups(request.parent_phc_id)
    group = groups[0] if groups else legacy.MultiAgentGroup(group_id='group_'+request.parent_phc_id,
        group_name='Octopus companions', parent_agent_id=request.parent_phc_id, sub_agents=[],
        communication_config={'protocol':'ANP','scope':'local'}, created_at=child.created_at)
    group.sub_agents.append(child)
    legacy.save_agent_group(group)
    return {'success': True, 'child': {'id':child_id, 'phc_id':child_id, 'name':child.name,
                                     'agent_type':'openclaw', 'role':'executor'}}

class ChildRequest(BaseModel):
    agent_type: str | None = Field(default=None,pattern='^(octopus|openclaw)$')
    parent_phc_id: str = Field(max_length=120)
    name: str = Field(min_length=1, max_length=32)
    description: str = Field(default='', max_length=500)
    capabilities: list[str] = Field(default_factory=list, max_length=10)

@router.get('/{parent_id}')
def children(parent_id: str):
    runtime.agent_dir(parent_id.replace(':', '_'))
    result = []
    for group in legacy.list_agent_groups(parent_id):
        for child in group.sub_agents:
            item = {'id':child.id, 'name':child.name, 'phc_id':child.phc_id,
                    'created_at':child.created_at, 'group_id':group.group_id}
            try:
                path = runtime.agent_dir(child.phc_id)
                kind = 'openclaw' if (path / 'openclaw_package').is_dir() else 'octopus'
                item.update(agent_type=kind, role='executor' if kind=='openclaw' else 'assistant')
                live = runtime.snapshot(child.phc_id)
                item.update(stage=live['stage'], message=live['message'])
            except HTTPException:
                item.update(stage='unavailable', message='旧实例缺少运行清单，请重新创建或由管理员迁移。')
            result.append(item)
    return {'success':True, 'children':result}

@router.post('/create')
async def create_child(request: ChildRequest):
    if not re.fullmatch(r'[\w\-\u4e00-\u9fff ]{1,32}', request.name) or not request.name.strip():
        raise HTTPException(400, '名称只能包含中英文、数字、空格、下划线和短横线')
    parent = runtime.agent_dir(request.parent_phc_id.replace(':', '_'))
    from app.deletion_review import frozen
    if frozen(parent.name):
        raise HTTPException(409, '主智能体已申请删除，暂不能创建子智能体')
    available=[kind for kind,folder in [('octopus','octopus_build'),('openclaw','openclaw_package')] if (parent/folder).is_dir()]
    if len(available)!=1:
        raise HTTPException(409,'主智能体运行包缺失或类型不明确，请检查主实例配置')
    kind=available[0]
    if kind == 'openclaw':
        raise HTTPException(400, 'OpenClaw 仅作为独立身份认证实例，不支持创建子智能体')
    octopus = (request.agent_type or 'octopus') == 'octopus'
    supported={'text-processing','news-search','web-browsing','webchat'} if octopus else {'browser','file_access','shell','canvas','memory','camera','webchat'}
    if not set(request.capabilities) <= supported:
        raise HTTPException(400, '存在不支持的能力')
    if not CREATE_LOCK.acquire(blocking=False):
        raise HTTPException(409, '另一个子智能体正在创建，请稍后重试')
    try:
        if octopus:
            return create_octopus_child(request,parent)
        return create_openclaw_branch(request, parent)
    except HTTPException:
        raise
    except Exception:
        reference = uuid.uuid4().hex[:12]
        logger.exception('Child creation failed; reference=%s', reference)
        raise HTTPException(500, f'子智能体创建失败，请管理员查看用户服务日志（错误编号：{reference}）后重试。') from None
    finally:
        CREATE_LOCK.release()
