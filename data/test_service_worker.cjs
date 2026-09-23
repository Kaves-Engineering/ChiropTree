// No browser dependency: check bounded precaching and failed-install cleanup.
const vm=require('node:vm');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../service-worker.js'),'utf8');

async function check(fail){
  let active=0,peak=0,activated=0;
  const added=[],deleted=[];
  const context=vm.createContext({
    self:{addEventListener(){},async skipWaiting(){activated++}},
    caches:{
      async open(){return {async add(url){
        active++;peak=Math.max(peak,active);
        try{
          await new Promise(resolve=>setTimeout(resolve,1));
          if(fail && url==='./index.html')throw Error('download failed');
          added.push(url);
        }finally{active--}
      }}},
      async delete(name){deleted.push(name)}
    }
  });
  vm.runInContext(source,context);
  if(fail){
    await assert.rejects(context.installCore(),/download failed/);
    assert.equal(activated,0,'partial offline library must not activate');
    assert.deepEqual(deleted,[vm.runInContext('CACHE',context)]);
  }else{
    await context.installCore();
    assert.deepEqual(added.sort(),Array.from(vm.runInContext('CORE',context)).sort());
    assert.equal(activated,1);
  }
  assert(peak<=2,'at most two precache downloads at a time');
}
(async()=>{await check(false);await check(true);console.log('Service worker precache checks PASS')})().catch(e=>{console.error(e);process.exitCode=1});
