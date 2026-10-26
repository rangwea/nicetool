'use strict';
const translations = {
  'zh-CN': {
    'demo.illustrated':'AI 生成流程示意','demo.recorded':'NiceTool 工作台 · 真实录制',
    skip:'跳至内容','nav.demos':'流程演示','nav.workflow':'如何工作','nav.docs':'使用文档','nav.start':'开始体验 ↗',
    'hero.eyebrow':'一句需求，一个顺手的工具。','hero.tagline':'你的想法，团队的工具。','hero.description':'在 Codex 中描述需求，预览 AI 做出的工具。确认后发布，让团队在 NiceTool 工作台直接使用。','hero.primary':'看看完整流程 ↓','hero.secondary':'阅读使用文档 ↗','hero.note':'自行部署 · 项目授权 · MIT 开源','hero.window':'AI 创建 → 团队使用','hero.live':'从需求到工作台',
    'demos.eyebrow':'01 / 从想法到可用','demos.title':'跟着一个工具，走完完整流程。','demos.description':'Codex Desktop 的创建与发布采用 AI 生成流程示意，NiceTool 工作台的预览与使用来自真实录制。','demos.note':'创建与发布片段为 AI 生成流程示意。工作台片段为真实录制，仅使用合成数据。“部署”指发布工具到已运行的 NiceTool 实例。',
    'tab.create':'Codex Desktop 生成','tab.preview':'预览验证','tab.publish':'发布部署','tab.use':'NiceTool 工作台','demo.play':'播放演示','demo.pause':'暂停演示','demo.guide':'自己动手试试 ↗',
    'workflow.eyebrow':'02 / 各司其职，顺畅衔接','workflow.title':'AI 负责创建，NiceTool 承接日常。','workflow.description':'创作者留在熟悉的 AI 编程助手里，团队通过浏览器访问 NiceTool 工作台。',
    'step.one.title':'描述需求','step.one.copy':'安装 NiceTool Skill，告诉 Codex 你需要哪些数据、操作和结果。','step.two.title':'预览与调整','step.two.copy':'在 NiceTool 工作台检查交互与结果，结合日志继续完善，确认后再发布。','step.three.title':'在 NiceTool 工作台使用','step.three.copy':'按项目组织和授权，让工具成为可以反复使用、持续维护的团队资源。',
    'features.eyebrow':'03 / 为持续使用准备','features.title':'不止生成一次，更要一直好用。','feature.one.title':'统一的工具中心','feature.one.copy':'搜索、筛选、按项目浏览。把散落的脚本变成团队找得到、用得上的工具。','feature.two.title':'共享的数据能力','feature.two.copy':'集中管理 MySQL、MongoDB、变量和枚举，让新工具复用已有资源。','feature.three.title':'版本和运行日志','feature.three.copy':'保留工具版本，查看执行日志，必要时回滚源码，支持后续迭代。','feature.four.title':'面向团队的授权','feature.four.copy':'支持账号、OIDC/OAuth2 和项目权限，将工具分享给需要的成员。',
    'faq.eyebrow':'开始之前','faq.title':'你可能还想知道。','faq.more':'查看完整文档 ↗','faq.one.q':'需要在 NiceTool 里配置模型吗？','faq.one.a':'工具创建与修改由外部 AI 编程助手完成，例如安装了 NiceTool Skill 的 Codex。平台本身不要求配置模型密钥；数据会按照所用助手及模型的配置处理。','faq.two.q':'演示是预置功能，还是 AI 创建的工具？','faq.two.a':'订单工作台是为演示创建的 NiceTool 工具，使用固定的合成订单数据。你可以按自己的需求创建不同的工具，而不局限于这些界面。','faq.three.q':'“发布部署”会替我部署整个平台吗？','faq.three.a':'不会。这里的发布是把工具源码上传到已部署的 NiceTool 实例。平台可通过 Docker 或 Python + MySQL 自行部署，具体步骤见文档。','faq.four.q':'适合让任何人上传代码吗？','faq.four.a':'工具代码在服务进程内执行。请将发布权限授予可信创作者，并根据数据敏感度配置认证、项目授权和预览访问策略。',
    'closing.eyebrow':'从每天重复的那件小事开始。','closing.title':'下一件顺手的工具，交给 AI 和你。','closing.copy':'先用合成数据跑通，再接入你的真实业务。','closing.button':'开始本地体验 ↗','footer.copy':'让想法成为团队可用的工具。','footer.docs':'文档 ↗'
  },
  'en-US': {
    'demo.illustrated':'AI-generated workflow illustration','demo.recorded':'NiceTool Workspace · recorded interface',
    skip:'Skip to content','nav.demos':'See it in action','nav.workflow':'How it works','nav.docs':'Documentation','nav.start':'Get started ↗',
    'hero.eyebrow':'One idea. A tool that fits.','hero.tagline':'Your ideas. Your team’s tools.','hero.description':'Describe a task in Codex. Preview the AI-built tool. Publish when it is ready, and let your team use it in NiceTool Workspace.','hero.primary':'Watch the workflow ↓','hero.secondary':'Read the docs ↗','hero.note':'Self-hosted · Project permissions · MIT licensed','hero.window':'AI creates → Your team uses','hero.live':'From idea to workspace',
    'demos.eyebrow':'01 / FROM IDEA TO EVERYDAY','demos.title':'One tool. The complete journey.','demos.description':'Codex Desktop creation and publishing use AI-generated workflow illustrations. NiceTool Workspace preview and usage show the running application.','demos.note':'Creation and publishing are AI-generated workflow illustrations. Workspace clips are real recordings with synthetic data. Deployment here means publishing a tool to a running NiceTool instance.',
    'tab.create':'Create in Codex Desktop','tab.preview':'Preview & verify','tab.publish':'Publish & deploy','tab.use':'NiceTool Workspace','demo.play':'Play demo','demo.pause':'Pause demo','demo.guide':'Try it yourself ↗',
    'workflow.eyebrow':'02 / A SIMPLE HANDOFF','workflow.title':'AI builds it. NiceTool makes it useful.','workflow.description':'Creators work in their AI coding assistant. Teams access NiceTool Workspace through a browser.',
    'step.one.title':'Describe the task','step.one.copy':'Install the NiceTool Skill and tell Codex what data, actions and results you need.','step.two.title':'Preview and refine','step.two.copy':'Check the interaction and results in NiceTool Workspace. Use logs to refine the tool before publishing.','step.three.title':'Use in NiceTool Workspace','step.three.copy':'Organize and authorize by project. Turn a one-off script into a resource your team can keep using.',
    'features.eyebrow':'03 / BUILT FOR THE NEXT DAY','features.title':'Useful once. Better every day.','feature.one.title':'One place for your tools','feature.one.copy':'Search, filter and browse by project. Make scattered scripts easy to find and use.','feature.two.title':'Shared data resources','feature.two.copy':'Manage MySQL, MongoDB, variables and enums centrally, so every new tool can reuse them.','feature.three.title':'Versions and runtime logs','feature.three.copy':'Keep source versions, inspect execution logs and roll back source when needed.','feature.four.title':'Access for your team','feature.four.copy':'Use accounts, OIDC/OAuth2 and project permissions to share tools with the right people.',
    'faq.eyebrow':'BEFORE YOU START','faq.title':'A few things to know.','faq.more':'Read all the docs ↗','faq.one.q':'Do I configure a model in NiceTool?','faq.one.a':'An external AI coding assistant, such as Codex with the NiceTool Skill, creates and updates tools. NiceTool itself does not require a model API key. Data handling depends on the assistant and model you use.','faq.two.q':'Are these built-in features or AI-created tools?','faq.two.a':'The order workspace is a NiceTool tool created for this demonstration. It uses fixed synthetic orders. You can create different tools for your own tasks.','faq.three.q':'Does publishing deploy the entire platform?','faq.three.a':'No. Publishing uploads tool source to an already deployed NiceTool instance. Deploy the platform separately with Docker or Python and MySQL; the docs explain how.','faq.four.q':'Can anyone upload code?','faq.four.a':'Tool code runs in the service process. Grant publishing permissions to trusted creators, and configure authentication, project access and preview policies for your data.',
    'closing.eyebrow':'START WITH THE TASK YOU REPEAT.','closing.title':'Your next useful tool starts with you.','closing.copy':'Try it with synthetic data. Then make it your own.','closing.button':'Try it locally ↗','footer.copy':'Turn ideas into tools your team can use.','footer.docs':'Documentation ↗'
  }
};
const demos = {
  create: {kicker:'CODEX DESKTOP × NICETOOL',zh:['描述需求，让 Codex 创建工具。','读取 NiceTool Skill 后，Codex 为合成订单创建工作台源码。',['生成单文件 NiceTool 工具','筛选、指标、表格与 CSV 导出','通过 Python 语法和入口校验'],'流程示意 · 输入需求 → 生成工具 → 右侧预览。'],en:['Describe it. Let Codex build it.','With the NiceTool Skill as context, Codex creates an order workspace from synthetic data.',['One NiceTool source file','Filters, metrics, tables and CSV export','Python syntax and entry-point checks'],'Workflow illustration · describe → create → preview.']},
  preview:{kicker:'PREVIEW → VERIFY',zh:['先在 NiceTool 工作台，确认它好用。','上传源码生成预览，打开真实界面，检查筛选和结果。',['预览与正式工具分开','使用合成订单验证筛选','确认交互后再发布'],'NiceTool 临时预览的真实界面录制。'],en:['See it work before sharing it.','Upload the source for a preview. Open the real interface and verify the filters and results.',['Preview stays separate from published tools','Check filters against synthetic orders','Verify the interaction before publishing'],'Recorded from a running NiceTool temporary preview.']},
  publish:{kicker:'VERIFY → PUBLISH',zh:['验证完成，发布到团队入口。','在 Codex Desktop 中使用 NiceTool Skill 发布已验证工具，并核对正式状态。',['明确上传待发布源码','数据库保存正式版本','核对发布状态与工具地址'],'流程示意 · 输入“部署” → 发布 → 工作台使用。'],en:['Verified. Published. Ready to share.','Use the NiceTool Skill in Codex Desktop to publish a verified tool and check its state.',['Explicit source upload','Published versions stored in the database','Verify the state and tool URL'],'Workflow illustration · deploy → publish → workspace.']},
  use:{kicker:'TEAM → NICETOOL WORKSPACE',zh:['下次需要时，直接打开使用。','从工具中心进入订单工作台，查询客户订单，并导出当前筛选结果。',['在 NiceTool 工作台使用','组合关键词和状态筛选','导出当前结果，不是全部数据'],'真实运行界面；仅使用合成订单。'],en:['Open it. Use it. Come back tomorrow.','Open the order workspace, find customer orders and export the currently filtered results.',['Use it in NiceTool Workspace','Combine keyword and status filters','Export the matching rows, not everything'],'Actual running interface, using synthetic orders only.']}
};
let language = 'zh-CN';
let activeDemo = 'create';
let playing = false;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
function savedLanguage(){try{return localStorage.getItem('nicetool-website-language');}catch{return null;}}
function renderDemo(){
  const short = language === 'en-US' ? 'en' : 'zh';
  const data = demos[activeDemo][short];
  document.getElementById('demo-kicker').textContent = demos[activeDemo].kicker;
  document.getElementById('demo-title').textContent = data[0];
  document.getElementById('demo-description').textContent = data[1];
  document.getElementById('demo-details').replaceChildren(...data[2].map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
  document.getElementById('demo-caption').textContent = data[3];
  const image = document.getElementById('demo-image');
  const illustrated = activeDemo === 'create' || activeDemo === 'publish';
  image.hidden = illustrated;
  document.getElementById('desktop-demo').hidden = !illustrated;
  if(illustrated)desktopDemo.update(short,activeDemo,playing);else desktopDemo.stop();
  document.getElementById('desktop-demo').setAttribute('aria-label',data[0]);
  image.src = `assets/demos/${activeDemo}-${short}.${playing ? 'gif' : 'webp'}?v=workspace-list-v5`;
  document.getElementById('media-kind').textContent = translations[language][illustrated ? 'demo.illustrated' : 'demo.recorded'];
  image.alt = data[0];
  const toggle = document.getElementById('play-toggle');
  toggle.textContent = translations[language][playing ? 'demo.pause' : 'demo.play'];
  toggle.setAttribute('aria-pressed',String(playing));
  document.querySelectorAll('[data-demo]').forEach(tab=>{const active=tab.dataset.demo===activeDemo;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});
  document.getElementById('demo-panel').setAttribute('aria-labelledby',`tab-${activeDemo}`);
}
function setLanguage(value){
  language = translations[value] ? value : 'zh-CN';
  document.documentElement.lang = language;
  document.title = language === 'en-US' ? 'NiceTool — Your ideas. Your team’s tools.' : 'NiceTool — 你的想法，团队的工具。';
  document.querySelector('meta[name="description"]').content=translations[language]['hero.description'];
  document.querySelectorAll('[data-i18n]').forEach(node=>{node.textContent=translations[language][node.dataset.i18n];});
  const toggle=document.querySelector('[data-language-toggle]');
  toggle.textContent=language==='en-US'?'中文':'EN';
  toggle.setAttribute('aria-label',language==='en-US'?'切换为中文':'Switch to English');
  heroDemo.update(language==='en-US'?'en':'zh','create',false);
  document.getElementById('hero-workflow').setAttribute('aria-label',language==='en-US'?'Codex creates an order tool. Your team uses it in NiceTool Workspace.':'Codex 生成订单工具，团队在 NiceTool 工作台使用');
  try{localStorage.setItem('nicetool-website-language',language);}catch{/* Optional preference storage. */}
  renderDemo();
}
document.querySelector('[data-language-toggle]').addEventListener('click',()=>setLanguage(language==='zh-CN'?'en-US':'zh-CN'));
document.querySelectorAll('[data-demo]').forEach(tab=>{
  tab.addEventListener('click',()=>{activeDemo=tab.dataset.demo;playing=false;renderDemo();});
  tab.addEventListener('keydown',event=>{
    const tabs=[...document.querySelectorAll('[data-demo]')];
    const index=tabs.indexOf(tab);
    let next;
    if(event.key==='ArrowRight')next=(index+1)%tabs.length;
    if(event.key==='ArrowLeft')next=(index-1+tabs.length)%tabs.length;
    if(event.key==='Home')next=0;
    if(event.key==='End')next=tabs.length-1;
    if(next!==undefined){event.preventDefault();tabs[next].click();tabs[next].focus();}
  });
});
document.getElementById('play-toggle').addEventListener('click',()=>{playing=!playing;renderDemo();});
document.querySelector('.menu-toggle').addEventListener('click',event=>{const open=document.getElementById('nav-links').classList.toggle('open');event.currentTarget.setAttribute('aria-expanded',String(open));});
document.querySelectorAll('.nav-links a').forEach(link=>link.addEventListener('click',()=>{document.getElementById('nav-links').classList.remove('open');document.querySelector('.menu-toggle').setAttribute('aria-expanded','false');}));
reducedMotion.addEventListener('change',()=>{if(reducedMotion.matches){playing=false;renderDemo();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden && playing){playing=false;renderDemo();}});
setLanguage(savedLanguage() || (navigator.language.toLowerCase().startsWith('zh')?'zh-CN':'en-US'));
