'use strict';
(() => {
 const panel=document.createElement('section');panel.className='panel anp-panel';panel.hidden=true;
 panel.innerHTML='<h2>主子伙伴通信 <small>ANP</small></h2><p class="muted">启动双方后，通过本机 ANP 网关互发消息。记录保存在本地，重启后可查看；收到消息不代表模型执行了任务。</p><form id="anp-form"><label>发送给<select id="anp-target" required></select></label><label>消息内容<textarea id="anp-content" required maxlength="4000" rows="3" placeholder="给伙伴留一条消息"></textarea></label><button class="primary" id="anp-send">发送消息</button> <button type="button" class="secondary" id="anp-refresh">刷新消息</button></form><p id="anp-status" role="status"></p><h3>收件箱</h3><div id="anp-inbox"></div><h3>发送记录</h3><div id="anp-outbox"></div>';
 document.querySelector('#partner-detail').append(panel);
 let currentType='octopus';let current='',version=0,draft=null,sending=false;
 const el=id=>panel.querySelector('#'+id);
 const endpoint=()=>'/user/anp/';
 const transport=()=>'ANP';
 const labels={delivered:'已接收',failed:'投递未确认',pending:'等待确认',received:'已收到'};
 async function inbox(){const v=version;try{
  const data=await api(endpoint()+encodeURIComponent(current));if(v!==version)return;
  el('anp-status').textContent=data.connected?transport()+'已就绪 · 消息记录已更新':transport()+'未就绪 · 可查看历史消息，发送前请启动双方';
  if(data.identity_memory){const m=data.identity_memory;el('anp-status').textContent+=` · 行为图谱 ${m.events} 条可信事件 · `+(m.last_auth?.mode==='history'?'最近接收：历史挑战认证通过':m.last_auth?.mode==='bootstrap'?'最近接收：首次密钥认证通过，已建立行为记忆':'尚无接收认证记录');}
  for(const [id,items] of [['anp-inbox',data.messages||[]],['anp-outbox',data.sent||[]]]){
   el(id).replaceChildren();for(const message of items){const row=document.createElement('div');row.className='anp-message';const text=document.createElement('p');text.textContent=`${id==='anp-inbox'?message.sender_did:message.target_id} · ${message.timestamp}\n${message.content}\n${labels[message.status]||''}`;row.append(text);
    if(id==='anp-outbox'&&['failed','pending'].includes(message.status)){const retry=document.createElement('button');retry.className='secondary';retry.textContent='重试这条消息';retry.disabled=sending;retry.onclick=()=>transmit({target_id:message.target_id,content:message.content,message_id:message.message_id});row.append(retry);}el(id).append(row);
   }if(!items.length)el(id).textContent=id==='anp-inbox'?'暂未收到消息。':'暂无发送记录。';
  }
 }catch(e){if(v===version)el('anp-status').textContent=e.message;}}
 async function select(id,type=currentType){currentType=type;current=id;const v=++version;draft=null;sending=false;panel.hidden=currentType!=='octopus';if(panel.hidden)return;
  panel.querySelector('h2').textContent='同组伙伴通信 · '+transport();
  panel.querySelector('p.muted').textContent='启动双方后，通过本机 ANP 网关互发消息。记录保存在本地；收到消息不代表模型执行了任务。';
  el('anp-target').replaceChildren();el('anp-content').value='';el('anp-inbox').replaceChildren();el('anp-outbox').replaceChildren();el('anp-status').textContent='请启动双方后发送，或刷新消息查看历史记录。';
  try{const data=await api('/user/children/'+encodeURIComponent(state.phc.id));if(v!==version)return;const members=[{phc_id:state.phc.id.replaceAll(':','_'),name:'主智能体'},...data.children.filter(item=>item.agent_type!=='openclaw')];for(const item of members){if(item.phc_id===current)continue;const option=document.createElement('option');option.value=item.phc_id;option.textContent=item.name;el('anp-target').append(option);}el('anp-send').disabled=!el('anp-target').options.length;}catch(e){if(v===version)el('anp-status').textContent=e.message;}
 }
 async function transmit(body){if(sending)return;const v=version;sending=true;el('anp-send').disabled=true;el('anp-status').textContent='正在通过'+transport()+'投递…';
  try{const data=await api(endpoint()+encodeURIComponent(current)+'/send',body);if(v!==version)return;el('anp-content').value='';draft=null;await inbox();if(v===version)el('anp-status').textContent='对方已接收 · 回执 '+data.receipt.message_id;}
  catch(e){if(v===version){await inbox();if(v===version)el('anp-status').textContent=e.message+'。可重试同一条消息，不会重复入箱。';}}
  finally{if(v===version){sending=false;el('anp-send').disabled=!el('anp-target').options.length;panel.querySelectorAll('#anp-outbox button').forEach(button=>button.disabled=false);}}
 }
 el('anp-refresh').onclick=inbox;
 el('anp-form').onsubmit=event=>{event.preventDefault();const target_id=el('anp-target').value,content=el('anp-content').value;if(!content.trim())return;
  if(!draft||draft.target_id!==target_id||draft.content!==content)draft={target_id,content,message_id:crypto.randomUUID()};transmit(draft);
 };
 window.addEventListener('runtime-selected',event=>select(event.detail.id,event.detail.agent_type||state.type));
 window.addEventListener('children-updated',()=>{if(current)select(current);});
 window.addEventListener('agent-record-ready',()=>{if(!current&&state.phc?.id)select(state.phc.id.replaceAll(':','_'));});
 if(state.phc?.id)select(state.phc.id.replaceAll(':','_'));
})();
