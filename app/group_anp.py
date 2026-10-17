"""Local Octopus group routing and browser access. No model calls."""
import json
import secrets
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app import experience_runtime as rt

LOCK=threading.RLock()
gateway=None
ports=None
router=APIRouter(prefix='/user/anp',dependencies=[Depends(rt.guard)])

def registry_path(parent):
    return rt.ROOT/'local_store/anp_groups'/f'{parent}.json'

def group_for(agent_id):
    path=rt.agent_dir(agent_id)
    if not any((path/name).is_dir() for name in ('octopus_build','openclaw_package')):raise HTTPException(400,'实例缺少运行包')
    manifest=json.loads((path/'agent_manifest.json').read_text(encoding='utf-8'))
    parent=str(manifest.get('parent_phc_id') or agent_id).replace(':','_')
    rt.agent_dir(parent)
    return parent

def ensure_gateway():
    global gateway,ports
    with LOCK:
        if gateway and gateway.poll() is None:return ports
        http=rt.reserve_port(ports[0] if ports else 0);ws=rt.reserve_port(ports[1] if ports else 0)
        while ws==http:ws=rt.reserve_port(0)
        log=rt.ROOT/'local_store/anp-gateway.log';log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w',encoding='utf-8') as output:
            gateway=subprocess.Popen([sys.executable,str(rt.ROOT/'app/local_anp_gateway.py'),str(http),str(ws)],
                cwd=rt.ROOT,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=rt.HIDDEN)
        for _ in range(60):
            if gateway.poll() is not None:break
            try:
                with httpx.Client(trust_env=False,timeout=.5) as client:
                    if client.get(f'http://127.0.0.1:{http}/health').status_code==200:
                        ports=(http,ws);return ports
            except httpx.HTTPError:pass
            time.sleep(.2)
        rt.kill(gateway)
        raise RuntimeError('ANP 网关未启动，请检查 local_store/anp-gateway.log 和 anp-proxy 依赖')

def prepare(agent_id,port):
    parent=group_for(agent_id)
    http,ws=ensure_gateway()
    with LOCK:
        path=registry_path(parent);path.parent.mkdir(parents=True,exist_ok=True)
        data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'members':{}}
        from app.identity_memory import provision
        public_key=provision(rt.agent_dir(agent_id))
        old_key=data['members'].get(agent_id,{}).get('memory_public_key')
        if old_key and old_key!=public_key:
            raise RuntimeError('行为身份密钥发生变化，请检查原实例密钥，不能自动替换身份')
        data.update(gateway_http=f'http://127.0.0.1:{http}',gateway_ws=f'ws://127.0.0.1:{ws}')
        data['members'][agent_id]={'port':port,'token':secrets.token_urlsafe(32),'memory_public_key':public_key}
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(path)
    return {'OCTOPUS_GROUP_FILE':str(path),'OCTOPUS_INSTANCE_ID':agent_id}

def member(agent_id):
    parent=group_for(agent_id)
    path=registry_path(parent)
    if not path.exists():raise HTTPException(409,'请先启动主智能体和子智能体以启用 ANP')
    data=json.loads(path.read_text(encoding='utf-8'))
    info=data['members'].get(agent_id)
    if not info or rt.snapshot(agent_id)['stage']!='ready':raise HTTPException(409,'请先启动该智能体')
    return parent,info

def local_call(agent_id,method,suffix,body=None):
    _,info=member(agent_id)
    ensure_gateway()
    try:
        with httpx.Client(trust_env=False,timeout=20) as client:
            response=client.request(method,f"http://127.0.0.1:{info['port']}/local-anp/{suffix}",
                headers={'Authorization':'Bearer '+info['token']},json=body)
        if response.status_code!=200:raise HTTPException(409,'ANP 通信未完成，请确认双方已重新启动并连接网关')
        return response.json()
    except (httpx.HTTPError,ValueError):raise HTTPException(409,'ANP 连接不可用，请重新启动该智能体')

class Send(BaseModel):
    message_id:str=Field(default_factory=lambda:uuid.uuid4().hex,pattern=r'^[A-Za-z0-9_-]{1,80}$')
    target_id:str=Field(max_length=120)
    content:str=Field(min_length=1,max_length=4000)

@router.get('/{agent_id}')
def state(agent_id:str):
    group_for(agent_id)
    try:return local_call(agent_id,'GET','messages')
    except HTTPException as exc:
        if exc.status_code!=409:raise
        from app.anp_mailbox import Mailbox
        box=Mailbox(rt.agent_dir(agent_id)/'anp_messages.sqlite3')
        return {'success':True,'connected':False,'messages':box.listing('in'),'sent':box.listing('out'),'message':exc.detail}

@router.post('/{agent_id}/send')
def send(agent_id:str,body:Send):
    parent=group_for(agent_id);other=group_for(body.target_id)
    if parent!=other or agent_id==body.target_id:raise HTTPException(403,'仅允许同一主智能体组内通信')
    if not body.content.strip():raise HTTPException(400,'请填写消息内容')
    from app.anp_mailbox import Mailbox
    box=Mailbox(rt.agent_dir(agent_id)/'anp_messages.sqlite3')
    row=box.reserve('out',agent_id,body.message_id,body.target_id,body.content)
    if row['receipt']:return {'success':True,'receipt':json.loads(row['receipt']),'transport':'ANP / ANPX'}
    try:
        member(body.target_id)
        return local_call(agent_id,'POST','send',body.model_dump())
    except (HTTPException,RuntimeError):
        box.finish('out',agent_id,body.message_id,'failed')
        raise

def shutdown():
    global gateway,ports
    with LOCK:
        rt.kill(gateway)
        if gateway:gateway.wait(timeout=5)
        gateway=None;ports=None
