"""Bounded restoration and configurable audit cleanup contracts."""
from datetime import datetime, timedelta, timezone
import pytest
from secure_gateway.engine.masking_engine import MaskingEngine
from secure_gateway.models import TokenMapping, TokenType
from secure_gateway.gateway_audit import AuditStore


def test_restore_limits_count_utf8_and_repeated_aliases():
    mapping=TokenMapping(original='고객'*20,surrogate='smcp_ID_1',token_type=TokenType.IDENTIFIER,context='code')
    engine=MaskingEngine(max_restore_input_bytes=100,max_restore_output_bytes=120)
    assert engine.unmask('smcp_ID_1','s',{'smcp_ID_1':mapping},strict=True).unmasked_text == '고객'*20
    with pytest.raises(ValueError,match='output size'):
        engine.unmask('smcp_ID_1 smcp_ID_1','s',{'smcp_ID_1':mapping})
    with pytest.raises(ValueError,match='input size'):
        engine.unmask('a'*101,'s',{})
    with pytest.raises(ValueError,match='output size'):
        MaskingEngine(max_restore_output_bytes=2).unmask('고객','s',{})


def test_audit_retention_dry_run_age_count_and_inflight(tmp_path):
    store=AuditStore(tmp_path/'logs.sqlite3',max_records=2,max_age_days=7)
    ids=[store.begin('a','p','s','/e','fixture') for _ in range(4)]
    with store.connect() as db:
        db.execute('UPDATE requests SET status=200 WHERE request_id != ?', (ids[-1],))
        db.execute('UPDATE requests SET started_at=? WHERE request_id=?',
                   ((datetime.now(timezone.utc)-timedelta(days=8)).isoformat(),ids[1]))
    before=store.query({})['summary']['total']
    report=store.retention()
    assert report['candidates']==2 and report['removed']==0
    assert store.query({})['summary']['total']==before
    assert store.retention(apply=True)['removed']==2
    rows=store.query({})['rows']
    assert {row['request_id'] for row in rows}=={ids[2],ids[3]}
    assert AuditStore(store.path,max_records=2,max_age_days=7).retention()['candidates']==0


@pytest.mark.parametrize('options',[{'max_records':0},{'max_age_days':False},{'max_age_days':-1}])
def test_invalid_retention_policy(tmp_path,options):
    with pytest.raises(ValueError):
        AuditStore(tmp_path/'logs.sqlite3',**options)

def test_installations_in_same_directory_have_separate_ownership(tmp_path,monkeypatch):
    from secure_gateway import gateway_install as install
    from secure_gateway.xai_install import install_api
    monkeypatch.setattr(install,'stop_gateway',lambda _:False)
    subscription=tmp_path/'config.json'
    api=tmp_path/'api.json'
    claude=tmp_path/'claude'
    claude.mkdir()
    grok=tmp_path/'grok'
    grok.mkdir()
    install.install_gateway(subscription,agent='claude',claude_dir=claude,startup_path=tmp_path/'startup')
    original=(claude/'settings.json').read_bytes()
    install.installation_path(subscription).read_bytes()
    install_api(api,'grok-fixture',port=38118,grok_dir=grok)
    assert install.installation_path(subscription)!=install.installation_path(api)
    assert install.uninstall_gateway(api)
    assert (claude/'settings.json').read_bytes()==original
    assert install.installation_path(subscription).exists()
    assert install.uninstall_gateway(subscription)

@pytest.mark.parametrize('strategy', __import__('secure_gateway.models',fromlist=['SurrogateStrategy']).SurrogateStrategy)
def test_new_korean_stems_apply_within_same_request(strategy):
    from secure_gateway.session import PrivacySession
    engine=MaskingEngine()
    session=PrivacySession('korean',strategy=strategy)
    source='루미노바 루미노바가'
    result=engine.mask_text(source,session.session_id,session.generator,session.forward_store,session.reverse_store)
    first,second=result.masked_text.split()
    assert second==first+'가'
    assert engine.unmask(result.masked_text,session.session_id,session.reverse_store,strategy,strict=True).unmasked_text==source

@pytest.mark.parametrize("invalid", [False, True])
@pytest.mark.parametrize("logout", [False, True])
def test_admin_relogin_during_pending_refresh_reopens_dashboard(tmp_path, invalid, logout):
    import shutil
    import subprocess
    from pathlib import Path
    node=shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    app=Path('src/secure_gateway/admin/app.js').read_text(encoding='utf-8')
    start=app.index('function render(data)')
    end=app.index('async function load()',start)
    app=app[:start]+'function render(data) {}\n'+app[end:]
    harness=r'''
const vm=require('vm');
const nodes={};
function get(id){return nodes[id] ||= {value:'',hidden:false,checked:false, handlers:{},
 addEventListener(name,fn){this.handlers[name]=fn},replaceChildren(){},focus(){},close(){},
 elements:{namedItem(){return {value:''}}}};}
let resolveFetch;let calls=0;let tasks=[];
const context={document:{getElementById:get,hidden:false},FormData:class{*[Symbol.iterator](){}},
 URLSearchParams, setInterval(){},setTimeout(fn){tasks.push(fn)},
 fetch(){calls++;return calls===2?new Promise(resolve=>resolveFetch=resolve):Promise.resolve({ok: !(calls===3 && INVALID),status:401,json:async()=>({})});}};
vm.createContext(context);
vm.runInContext(APP,context);
(async()=>{
 get('token').value='first';await get('login-form').handlers.submit({preventDefault(){}});
 if(!get('login').hidden)throw Error('initial login failed');
 let refresh=get('refresh').handlers.click();
 if(LOGOUT) get('logout').handlers.click();
 get('token').value='second';await get('login-form').handlers.submit({preventDefault(){}});
 resolveFetch({ok:true,json:async()=>({})});await refresh;
 while(tasks.length){await tasks.shift()();}
 if(INVALID){if(!LOGOUT) return; if(get('login').hidden)throw Error('invalid login opened dashboard');}
 else if(!get('login').hidden||get('dashboard').hidden)throw Error('relogin remained on login screen');
})().catch(error=>{console.error(error);process.exitCode=1});
'''.replace('APP',__import__('json').dumps(app)).replace('INVALID', str(invalid).lower()).replace('LOGOUT', str(logout).lower())
    script=tmp_path/'admin-test.js'
    script.write_text(harness,encoding='utf-8')
    result=subprocess.run([node,str(script)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr


def test_gateway_response_has_aggregate_restore_budget():
    import json
    from secure_gateway.gateway import GatewaySession
    session=GatewaySession(max_restore_output_bytes=100)
    alias=session.mask('PrivateCustomer'*5,code=True)
    with pytest.raises(ValueError,match='output size'):
        session.response(json.dumps({'output_text':alias,'other':alias}).encode(),'application/json')
    assert session.engine._restore_remaining is None


def test_custom_config_runtime_and_legacy_records_are_not_shared(tmp_path):
    import json
    from secure_gateway.gateway_install import runtime_directory,installation_path
    default=tmp_path/'config.json'
    custom=tmp_path/'custom.json'
    assert runtime_directory(default)!=runtime_directory(custom)
    legacy=tmp_path/'installation.json'
    legacy.write_text(json.dumps({'files':{str(custom.resolve()):{}}}))
    with pytest.raises(ValueError,match='Legacy shared'):
        installation_path(custom)
