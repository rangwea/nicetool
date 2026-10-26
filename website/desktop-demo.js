'use strict';
// A local, deterministic product walkthrough. No requests or tool publication.
function createDesktopDemo(hostId) {
  let frame = 0, elapsed = 0, previous = null, identity = '';
  let host, copy, stage;
  const words = {
    zh: {newChat:'新聊天',projects:'项目',title:'今天，想做一件什么工具？',hint:'描述需求，创建你的工具。',prompt:'创建订单查询工具，支持客户搜索、状态筛选和 CSV 导出。',deploy:'部署',deployTitle:'工具准备好了，发布到工作台。',placeholder:'和 Codex 一起工作',steps:['读取 NiceTool Skill','生成 order_workspace.py','检查入口并准备预览'],publishSteps:['检查已验证的工具源码','发布到 NiceTool 工作台','核对版本与访问地址'],reply:'工具已生成，在右侧检查预览。',published:'部署完成，团队可以在工作台打开工具。',preview:'工具预览',workspace:'NiceTool 工作台',orders:'订单工作台',total:'订单总数',revenue:'已完成金额',search:'搜索客户',status:'全部状态',completed:'已完成',customer:'客户',amount:'金额',export:'导出 CSV',ready:'已发布 · v1',filter:'筛选结果 · Acme',all:'合成订单 · 8 条',footer:'流程示意 · 合成数据'},
    en: {newChat:'New chat',projects:'Projects',title:'What should we build?',hint:'Describe a task. Create your tool.',prompt:'Create an order tool with customer search, status filters and CSV export.',deploy:'Deploy',deployTitle:'Ready to share with your team.',placeholder:'Work with Codex',steps:['Read NiceTool Skill','Create order_workspace.py','Check entry point and prepare preview'],publishSteps:['Check the verified tool source','Publish to NiceTool Workspace','Verify the version and tool URL'],reply:'Your tool is ready. Check the preview on the right.',published:'Published. Your team can open it in the workspace.',preview:'Tool preview',workspace:'NiceTool Workspace',orders:'Order workspace',total:'Total orders',revenue:'Completed revenue',search:'Search customers',status:'All statuses',completed:'Completed',customer:'Customer',amount:'Amount',export:'Export CSV',ready:'Published · v1',filter:'Filtered results · Acme',all:'Synthetic orders · 8 rows',footer:'Workflow illustration · synthetic data'}
  };
  function node(tag, className, value){const el=document.createElement(tag);el.className=className;if(value!==undefined)el.textContent=value;return el;}
  function mount(language, demo){
    cancelAnimationFrame(frame); frame=0; previous=null; elapsed=0;
    stage=demo;copy=words[language];host=document.getElementById(hostId);host.replaceChildren();
    const bar=node('div','desktop-titlebar');bar.append(node('span','desktop-dots','● ● ●'),node('span','','Codex'),node('span','desktop-scene-note',copy.footer));
    const body=node('div','desktop-body');
    const rail=node('aside','desktop-rail','◉\n\n◷\n\n▱\n\n⋯');
    const sidebar=node('aside','desktop-sidebar');sidebar.append(node('strong','','Codex'),node('div','desktop-new',`↗ ${copy.newChat}`),node('small','',copy.projects),node('div','desktop-project','▱ NiceTool'));
    const chat=node('div','desktop-chat');chat.append(node('div','desktop-chat-title',hostId==='hero-workflow'?(language==='zh'?'AI 创建工具':'AI creates your tool'):demo==='publish'?copy.deploy:copy.newChat));
    const welcome=node('div','desktop-welcome');welcome.append(node('strong','',demo==='publish'?copy.deployTitle:copy.title),node('p','',copy.hint));
    const conversation=node('div','desktop-conversation');conversation.append(node('div','desktop-message'),node('div','desktop-response'));
    const steps=node('div','desktop-steps');(demo==='publish'?copy.publishSteps:copy.steps).forEach(text=>steps.append(node('div','desktop-step',text)));conversation.append(steps,node('div','desktop-file','▤ order_workspace.py'),node('div','desktop-finished'));
    const composer=node('div','desktop-composer');composer.append(node('div','desktop-input',copy.placeholder),node('div','desktop-composer-tools','＋   ◇ NiceTool Skill'),node('span','desktop-send','↑'));
    chat.append(welcome,conversation,composer);
    const preview=node('div','desktop-preview');const address=node('div','desktop-address');address.append(node('span','','‹  ›  ↻'),node('span','desktop-url'));
    const content=node('div','desktop-tool');content.append(node('div','desktop-tool-label',demo==='publish'||hostId==='hero-workflow'?copy.workspace:copy.preview),node('h3','',copy.orders),node('div','desktop-published',copy.ready));
    const stats=node('div','desktop-stats');for(const [label,value] of [[copy.total,'8'],[copy.revenue,'$5,085.75']]){const card=node('div','');card.append(node('small','',label),node('strong','',value));stats.append(card);}
    const filters=node('div','desktop-filters');filters.append(node('span','desktop-search',copy.search),node('span','desktop-status',copy.status),node('span','desktop-export',copy.export));
    const table=node('table','desktop-table');const head=node('thead','');const tr=node('tr','');[copy.customer,copy.completed,copy.amount].forEach(value=>tr.append(node('th','',value)));head.append(tr);table.append(head);
    const tbody=node('tbody','');[['Acme','$1,240.00'],['Birch','$860.50'],['Cedar','$2,150.00'],['Acme','$430.25'],['Birch','$975.75'],['Cedar','$1,680.00'],['Acme','$2,150.00'],['Birch','$510.50']].forEach(([name,amount],i)=>{const row=node('tr','');row.dataset.matches=String(name==='Acme'&&i!==3);[name,i===1||i===5?'◷':'✓',amount].forEach(value=>row.append(node('td','',value)));tbody.append(row);});table.append(tbody);
    content.append(stats,filters,node('div','desktop-result-label',copy.all),table);preview.append(address,content);body.append(rail,sidebar,chat,preview);host.append(bar,body);paint(hostId==='hero-workflow'?11:0);
  }
  function paint(time){
    const prompt=stage==='publish'?copy.deploy:copy.prompt;
    const submitted=time>=3.5, opened=time>=9.8, filtered=stage==='create'&&time>=13;
    host.dataset.phase=opened?'preview':submitted?'generating':'typing';
    host.classList.toggle('has-preview',opened);
    host.querySelector('.desktop-welcome').hidden=submitted;
    host.querySelector('.desktop-conversation').hidden=!submitted;
    host.querySelector('.desktop-input').textContent=submitted?copy.placeholder:prompt.slice(0,Math.floor(Math.max(0,time-.6)/2.5*prompt.length));
    host.querySelector('.desktop-input').classList.toggle('is-typing',!submitted);
    host.querySelector('.desktop-message').textContent=prompt;
    host.querySelector('.desktop-response').textContent=stage==='publish'?copy.publishSteps[0]:copy.steps[0];
    host.querySelectorAll('.desktop-step').forEach((el,i)=>{const done=time>=5+i*1.5;el.classList.toggle('is-done',done);el.textContent=`${done?'✓':'◌'}  ${(stage==='publish'?copy.publishSteps:copy.steps)[i]}`;});
    host.querySelector('.desktop-file').hidden=time<7;
    host.querySelector('.desktop-finished').textContent=opened?(stage==='publish'?copy.published:copy.reply):'';
    host.querySelector('.desktop-preview').setAttribute('aria-hidden',String(!opened));
    host.querySelector('.desktop-url').textContent=stage==='publish'||hostId==='hero-workflow'?'nicetool / user / tools / orders':'nicetool / preview / order_workspace';
    host.querySelector('.desktop-published').hidden=stage!=='publish';
    host.querySelector('.desktop-search').textContent=filtered?'Acme':copy.search;
    host.querySelector('.desktop-status').textContent=filtered?copy.completed:copy.status;
    host.querySelector('.desktop-result-label').textContent=filtered?copy.filter:copy.all;
    host.querySelectorAll('tbody tr').forEach(row=>{row.hidden=filtered&&row.dataset.matches!=='true';});
    host.querySelector('.desktop-stats strong').textContent=filtered?'2':'8';
    host.querySelectorAll('.desktop-stats strong')[1].textContent=filtered?'$3,390.00':'$5,085.75';
  }
  function update(language,demo,playing){
    const key=`${language}:${demo}`;
    if(identity!==key){identity=key;mount(language,demo);}
    cancelAnimationFrame(frame);previous=null;
    host.classList.toggle('is-playing',playing);
    if(!playing)return;
    function tick(now){if(previous!==null)elapsed+=(now-previous)/1000;previous=now;elapsed%=26;paint(elapsed);frame=requestAnimationFrame(tick);}
    frame=requestAnimationFrame(tick);
  }
  function stop(){cancelAnimationFrame(frame);previous=null;identity='';}
  return {update,stop};
}
const desktopDemo = createDesktopDemo('desktop-demo');
const heroDemo = createDesktopDemo('hero-workflow');
