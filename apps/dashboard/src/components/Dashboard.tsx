'use client';
import {useState,useOptimistic,useTransition,useEffect,useRef} from 'react';
import Link from 'next/link';
import {useRouter,useSearchParams} from 'next/navigation';
import {QueryClient,QueryClientProvider,useQuery,useQueryClient} from '@tanstack/react-query';
import {Activity,ArrowDownToLine,ArrowUpRight,BarChart3,BookOpen,ChevronRight,Database,Gauge,Layers3,MapPinned,Menu,RefreshCw,X,Zap} from 'lucide-react';
import {AnalyticsPanel,DataTable} from './AnalyticsPanel';
import {RegionalMap} from './RegionalMap';
import {API,getData,number,stamp,londonMidnight,nextDate} from '@/lib/api';

const screens=[['overview','Overview',Gauge],['carbon','Carbon analytics',Activity],['generation','Generation & demand',Layers3],['regional','Regional intelligence',MapPinned],['forecasts','Forecast performance',BarChart3],['operations','Data operations',Database],['methodology','Methodology',BookOpen]] as const;
const copy:Record<string,[string,string]>={
 overview:['The grid, in perspective.','A connected view of Great Britain’s electricity system.'],
 carbon:['Understand the carbon signal.','Patterns, peaks and variability in electricity carbon intensity.'],
 generation:['Where the power comes from.','Generation composition and demand, with source definitions kept distinct.'],
 regional:['One grid. Different stories.','Compare carbon intensity across 14 electricity distribution regions.'],
 forecasts:['Measure the difference.','Published forecasts compared with national estimated actual intensity.'],
 operations:['Trust starts at the source.','Observe ingestion, freshness, revisions and the quality of persisted data.'],
 methodology:['Know what you’re measuring.','Definitions, provenance and the limits behind every signal.']};
export function Dashboard(){const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{staleTime:60000,retry:1,refetchOnWindowFocus:false}}}));return <QueryClientProvider client={client}><Workspace/></QueryClientProvider>}
function Workspace(){
 const search=useSearchParams();const router=useRouter();const qc=useQueryClient();
 const [optimisticSearch,setOptimisticSearch]=useOptimistic(search.toString());const [,startTransition]=useTransition();const filters=new URLSearchParams(optimisticSearch);
 const [menu,setMenu]=useState(false);const [run,setRun]=useState<string|null>(null);
 const dialogRef=useRef<HTMLElement>(null);
 useEffect(()=>{if(!run)return;const previous=document.activeElement as HTMLElement|null;const root=dialogRef.current;
 const controls=()=>Array.from(root?.querySelectorAll<HTMLElement>('button,a,input,select,[tabindex="0"]')||[]);
 controls()[0]?.focus();const handler=(event:KeyboardEvent)=>{if(event.key==='Escape')setRun(null);if(event.key==='Tab'){const items=controls();const first=items[0];const last=items[items.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}}};
 document.addEventListener('keydown',handler);return()=>{document.removeEventListener('keydown',handler);previous?.focus()};},[run]);

 const now=new Date();const week=new Date(now.getTime()-7*86400000);
 const screen=filters.get('screen')||'overview';const active=copy[screen]?screen:'overview';
 const start=filters.get('start')||week.toISOString().slice(0,10);const end=filters.get('end')||now.toISOString().slice(0,10);
 const region=filters.get('region')||'0';const granularity=filters.get('granularity')||'day';const fuel=filters.get('fuel')||'';const compare=filters.get('regions')||'1,2,3';
 const offset=Number(filters.get('offset')||0);const sort=filters.get('sort')||'asc';
 const params=new URLSearchParams({start:londonMidnight(start),end:londonMidnight(nextDate(end)),region,granularity,limit:'500',offset:String(offset),sort});
 if(fuel)params.set('fuel',fuel);params.set('regions',compare);
 const p=params.toString();
 function update(values:Record<string,string>){const s=new URLSearchParams(optimisticSearch);Object.entries(values).forEach(([k,v])=>v?s.set(k,v):s.delete(k));if(!('offset'in values))s.delete('offset');startTransition(()=>{setOptimisticSearch(s.toString());router.replace(`/?${s.toString()}`,{scroll:false})})}
 const regions=useQuery({queryKey:['regions'],queryFn:()=>getData('regions','')});
 const overview=useQuery({queryKey:['overview',p],queryFn:({signal})=>getData('overview',p,signal)});
 const values=overview.data?.rows[0]||{};const stale=overview.data?.meta.sources?.filter(s=>s.stale)||[];
 const forecast=useQuery({queryKey:['forecasts/errors',p],queryFn:({signal})=>getData('forecasts/errors',p,signal),enabled:active==='forecasts'});
 const operations=useQuery({queryKey:['operations/health',p],queryFn:({signal})=>getData('operations/health',p,signal),enabled:active==='operations'});
 const insight=useQuery({queryKey:['insights',p],queryFn:({signal})=>getData('insights',p,signal),enabled:active==='overview'});
 const detail=useQuery({queryKey:['run',run],queryFn:()=>getData(`operations/ingestion-runs/${run}`,''),enabled:!!run});
 const nav=(id:string)=>{update({screen:id,...(id==='regional'&&region==='0'?{region:'1'}:{})});setMenu(false)};
 const drill=(value:string)=>{if(/^\d{4}-\d{2}-\d{2}/.test(value)){update({start:value.slice(0,10),end:value.slice(0,10),granularity:'half-hour',screen:active==='regional'?'regional':'carbon'})}};
 const panel=(title:string,subtitle:string,route:string,kind='line',keys=['value'],x='time',wide=false)=><AnalyticsPanel key={route} {...{title,subtitle,route,params:p,kind,keys,x,wide}} onSelect={drill}/>;
 const exportName=({overview:'carbon',carbon:'carbon',generation:'generation',regional:'regions',forecasts:'forecasts',operations:'operations',methodology:'quality'} as Record<string,string>)[active];
 let metrics:[string,unknown,string][]=[['Latest intensity',values.latest,'gCO₂/kWh'],['Period average',values.mean,'gCO₂/kWh'],['Low-carbon mix',values.low_carbon,'%'],['Forecast MAE',values.mae,'gCO₂/kWh'],['Data completeness',values.completeness,'%']];
 if(active==='carbon')metrics=[['Period average',values.mean,'gCO₂/kWh'],['Minimum',values.minimum,'gCO₂/kWh'],['Maximum',values.maximum,'gCO₂/kWh'],['Volatility',values.volatility,'standard deviation'],['Previous-period Δ',values.change_percent,'%']];
 if(active==='generation')metrics=[['Low-carbon share',values.low_carbon,'%'],['Renewable share',values.renewable,'%'],['Fossil share',values.fossil,'%'],['Peak national demand',values.demand_peak,'MW']];
 if(active==='forecasts'){const v=forecast.data?.rows[0]||{};metrics=[['Mean absolute error',v.mae,'gCO₂/kWh'],['RMSE',v.rmse,'gCO₂/kWh'],['Signed bias',v.bias,'forecast − actual'],['95th percentile',v.p95,'absolute error'],['Paired intervals',v.paired_observations,'half hours']]}
 if(active==='operations'){const v=operations.data?.rows[0]||{};metrics=[['Ingestion runs',v.runs,'this period'],['Records received',v.received,'validated facts'],['Records rejected',v.rejected,'quarantined'],['Failure rate',v.failure_rate,'%'],['Mean duration',v.mean_duration_seconds,'seconds']]}
 return <div className="workspace"><a className="skip" href="#workspace-main">Skip to analytics</a>
 <aside id="workspace-sidebar" className={`sidebar ${menu?'open':''}`}><Link className="brand" href="/?screen=overview"><span className="brand-icon"><Zap size={19} strokeWidth={2.5}/></span>GridSignal<span className="brand-period">.</span></Link>
 <div className="workspace-label"><span className="live-dot"/> GB ELECTRICITY INTELLIGENCE</div><div className="nav-caption">WORKSPACE</div>
 <nav aria-label="Analytics screens">{screens.map(([id,label,Icon])=><button key={id} className={`nav-item ${id===active?'selected':''}`} aria-current={id===active?'page':undefined} onClick={()=>nav(id)}><Icon size={17}/><span>{label}</span>{id===active&&<ChevronRight size={14}/>}</button>)}</nav>
 <div className="sidebar-bottom"><div className="grid-art" aria-hidden="true"><i/><i/><i/><i/><i/><i/><i/></div><p>Complex systems.<br/><strong>Clearer signals.</strong></p><a href="https://victorokeke.co.uk" target="_blank" rel="noreferrer">Built by Victor Okeke <ArrowUpRight size={13}/></a><small>Official data. Open methodology.</small></div>
 </aside>{menu&&<button aria-label="Close navigation" className="menu-backdrop" onClick={()=>setMenu(false)}/>}
 <div className="main-shell"><header className="topbar"><div><button className="mobile-menu icon-button" aria-expanded={menu} aria-controls="workspace-sidebar" aria-label={menu?'Close navigation':'Open navigation'} onClick={()=>setMenu(!menu)}>{menu?<X size={19}/>:<Menu size={19}/>}</button><span className="breadcrumb">Workspace <ChevronRight size={12}/> <strong>{screens.find(s=>s[0]===active)?.[1]}</strong></span></div><div className="top-status"><span className={`live-dot ${stale.length?'warning':''}`}/>{overview.isError?'Connection unavailable':stale.length?'Coverage needs attention':'Sources connected'}<span className="gb-pill">GB</span></div></header>
 <main id="workspace-main"><div className="page-heading"><div><div className="eyebrow">SYSTEM INTELLIGENCE / {String(screens.findIndex(s=>s[0]===active)+1).padStart(2,'0')}</div><h1>{copy[active][0]}</h1><p>{copy[active][1]}</p></div><div className="page-actions"><button className="button" onClick={()=>qc.invalidateQueries()} aria-label="Refresh persisted analytics"><RefreshCw size={14}/>Refresh</button><a className="button button-primary" href={`${API}/export/${exportName}?${p}`}><ArrowDownToLine size={14}/>Export CSV</a></div></div>
 <section className="filterbar" aria-label="Analytical filters"><label>From<input type="date" value={start} max={end} onChange={e=>update({start:e.target.value})}/></label><span className="date-separator">→</span><label>To<input type="date" value={end} min={start} onChange={e=>update({end:e.target.value})}/></label>
 <label>Geography<select aria-label="Geography" value={region} onChange={e=>update({region:e.target.value})}><option value="0">Great Britain</option>{regions.data?.rows.filter(r=>r.scope==='region').map(r=><option key={String(r.id)} value={String(r.id)}>{r.name}</option>)}</select></label>
 <label>Resolution<select aria-label="Resolution" value={granularity} onChange={e=>update({granularity:e.target.value})}><option value="day">Daily</option><option value="hour">Hourly</option><option value="half-hour">Half-hourly</option></select></label>
 {active==='generation'&&<label>Fuel<select aria-label="Fuel" value={fuel} onChange={e=>update({fuel:e.target.value})}>{['','wind','solar','gas','nuclear','hydro','biomass','coal','imports','other','oil','pumped_storage'].map(f=><option key={f} value={f}>{f||'All fuels'}</option>)}</select></label>}
 <button className="text-button" onClick={()=>update({start:week.toISOString().slice(0,10),end:now.toISOString().slice(0,10),region:'0',granularity:'day',fuel:'',regions:'1,2,3'})}>Reset</button></section>
 {overview.isError&&<div className="notice error" role="alert">{overview.error.message} <button onClick={()=>overview.refetch()}>Retry connection</button></div>}
 {stale.length>0&&<div className="notice"><span className="notice-icon">!</span><span>{stale.length} source{stale.length>1?'s':''} outside freshness thresholds. Charts show persisted observations, with gaps preserved.</span><button className="text-button" onClick={()=>nav('operations')}>Inspect sources →</button></div>}
 {active!=='methodology'&&<section className="metrics" aria-label="Key indicators">{metrics.map(([label,value,unit],i)=><article className="metric" key={label}><div className="metric-label">{label}<ArrowUpRight size={13}/></div><div className={`metric-value ${i===0?'emphasis':''}`}>{overview.isPending?'…':number(value)}</div><div className="metric-unit">{unit}</div>{active==='overview'&&i===1&&values.change_percent!=null&&<div className="metric-note">{number(values.change_percent)}% vs previous period</div>}</article>)}</section>}
 {active==='overview'&&<><div className="section-title"><h2>The national picture</h2><span>Latest estimated actual · {stamp(values.latest_at)}</span></div><div className="charts-grid">
 {panel('Carbon intensity','National estimated actual and published forecast · gCO₂/kWh','carbon/trend','area',['actual','forecast'])}
 {panel('Electricity composition','Mean interval fuel shares · %','generation/mix','donut')}
 {panel('National demand','NESO periodically published outturn · MW','demand/profile','line',['national_mw','transmission_mw'])}
 {panel('Regional carbon landscape','14 subnational regions · forecast gCO₂/kWh','regions/ranking','ranking')}
 </div><section className="insights"><div className="eyebrow">SIGNALS WORTH A CLOSER LOOK</div>{insight.data?.rows.length?insight.data.rows.map((r,i)=><div key={i}><span className="insight-number">0{i+1}</span><p>{r.message}<small>{r.source} · observed {number(r.observed)} / reference {number(r.comparison)}</small></p><ArrowUpRight size={16}/></div>):<p>No threshold alerts for the current selection. This does not imply complete source coverage.</p>}</section></>}
 {active==='carbon'&&<><div className="charts-grid">
 {panel('Carbon intensity over time','Click a date to investigate half-hourly observations · gCO₂/kWh','carbon/trend','line',['value','rolling_7d','rolling_30d'], 'time',true)}
 {panel('The shape of a day','Hour-of-day means; weekend groups remain separate','carbon/profile','profile',['value'],'hour')}
 {panel('Intensity distribution','20 gCO₂/kWh bins · observation counts','carbon/distribution','bar',['observations'],'bucket')}
 {panel('Daily carbon heatmap','British reporting dates × local hour','carbon/heatmap','heatmap',[], 'time',true)}
 {panel('Period comparison','Equivalent preceding period, nulls excluded','carbon/comparison','table')}
 {panel('Half-hourly evidence','Source-linked observations; use sorting and pagination below','carbon/drilldown','table')}
 </div><Pagination {...{offset,sort,update}}/></>}
 {active==='generation'&&<div className="charts-grid">
 {panel('A changing generation mix','Source-reported composition · % · equal-interval means','generation/trend','stacked',[], 'time',true)}
 {panel('Fuel-share breakdown','Carbon API composition; separate from Elexon MW','generation/mix','donut')}
 {panel('Metered generation outturn','Elexon FUELHH · duration-weighted MW; not embedded-inclusive','generation/outturn','outturn')}
 {panel('National and transmission demand','Outturn A rows only; source publication can lag','demand/profile','line',['national_mw','transmission_mw'], 'time',true)}
 {panel('Weekdays and weekends','British hour-of-day demand · MW','demand/hourly','profile',['national_mw'],'hour')}
 {panel('Demand period comparison','Preceding equivalent period · MW','demand/comparison','table')}
 </div>}
 {active==='regional'&&<><div className="region-selector"><span>Compare regions</span>{regions.data?.rows.filter(r=>r.scope==='region').map(r=><label key={String(r.id)}><input type="checkbox" disabled={compare.split(',').length===1&&compare===String(r.id)} checked={compare.split(',').includes(String(r.id))} onChange={e=>{const ids=compare.split(',').filter(Boolean);update({regions:e.target.checked?[...ids,String(r.id)].join(','):ids.filter(id=>id!==String(r.id)).join(',')})}}/>{r.name}</label>)}</div><div className="charts-grid">
 {panel('Regional carbon rankings','Forecast intensity; country aggregates excluded','regions/ranking','ranking')}
 {panel('Across the same period','Multi-region forecast trajectories · gCO₂/kWh','regions/trend','multi')}
 <AnalyticsPanel title="Regional evidence" subtitle="Select Details to inspect one region" route="regions/ranking" params={p} kind="table" wide onRow={r=>update({region:String(r.id)})}/>
 {panel('Selected region versus national context','Regional forecast and national estimated actual · gCO₂/kWh','regions/benchmark','line',['regional','national'])}
 <RegionalMap params={p} onSelect={id=>update({region:id})}/>
 </div></>}
 {active==='forecasts'&&<><div className="method-note"><BookOpen size={16}/><p>These are <strong>published forecast–estimate differences</strong>, not verified issue-time forecast skill. National “actual” intensity is an estimate; source revisions are retained when observed.</p></div><div className="charts-grid">
 {panel('Forecast and estimated actual','Matched national intervals · gCO₂/kWh','forecasts/comparison','line',['forecast','actual'],'time',true)}
 {panel('Signed error through time','Positive means forecast exceeds estimated actual','forecasts/comparison','bar',['error'])}
 {panel('Error distribution','10 gCO₂/kWh signed-error bins','forecasts/distribution','bar',['observations'],'bucket')}
 {panel('Error by hour','British hour of day · MAE and signed bias','forecasts/hourly','bar',['mae','bias'],'hour')}
 {panel('Error by weekday','ISO day: Monday 1 → Sunday 7','forecasts/weekday','bar',['mae','bias'],'weekday')}
 {panel('Observed source revisions','Append-only differences from repeated source retrievals','forecasts/revisions','table',[],'time',true)}
 </div></>}
 {active==='operations'&&<div className="charts-grid">
 {panel('Source observability','Freshness is measured from source observation time, not polling time','operations/sources','table',[],'time',true)}
 {panel('Calendar coverage','Elapsed half-hour intervals; 46/48/50-period British days','operations/completeness','bar',['expected','usable'],'day')}
 {panel('Data-quality results','Persisted validation and freshness checks','operations/quality','table')}
 <AnalyticsPanel title="Ingestion activity" subtitle="Select a run to inspect its window, counters and status" route="operations/ingestion-runs" params={p} kind="table" wide onRow={r=>setRun(String(r.id))}/>
 </div>}
 {active==='methodology'&&<><section className="method-hero"><span className="eyebrow">FROM OBSERVATION TO DECISION</span><h2>Every number has a lineage.</h2><p>Official APIs → preserved raw responses → validated PostgreSQL facts → SQL analytical marts → FastAPI → this workspace.</p><div className="method-stages">{['Acquire','Validate','Persist','Analyse','Explain'].map((s,i)=><div key={s}><span>0{i+1}</span>{s}</div>)}</div></section><div className="charts-grid">
 {panel('Metric dictionary','Definitions, units, grains and caveats','metadata/metrics','table',[],'time',true)}
 {panel('Published carbon factors','Source-published factors, not a substitute for regional methodology','metadata/factors','table')}
 {panel('Coverage and last observations','Real source timestamps and freshness thresholds','operations/sources','table')}
 </div><div className="method-text"><h2>Reading the signals responsibly</h2><p>Carbon intensity is emissions per unit of electricity, not total emissions. National estimated actuals and regional forecasts are presented distinctly. Mean fuel shares are unweighted means of equal-duration observations, not energy-weighted period shares.</p><h3>Reporting calendar</h3><p>Observations retain UTC timestamps. Settlement dates and profiles use Europe/London, including the 46- and 50-period daylight-saving transition days. Missing observations remain missing; completeness uses an elapsed calendar denominator.</p><h3>Source schedules</h3><p>Carbon, regional and generation adapters poll every 30 minutes. Demand and published factors refresh daily; reconciliation runs every six hours. Polling frequency does not change source publication frequency.</p><h3>Source documentation</h3><a href="https://carbon-intensity.github.io/api-definitions/" target="_blank" rel="noreferrer">NESO Carbon Intensity API ↗</a><a href="https://bmrs.elexon.co.uk/api-documentation" target="_blank" rel="noreferrer">Elexon Insights API ↗</a><a href="https://www.neso.energy/data-portal/api-guidance" target="_blank" rel="noreferrer">NESO Data Portal ↗</a></div></>}
 <footer className="workspace-footer"><span><Zap size={12}/>GRIDSIGNAL / GB</span><p>Carbon intensity ≠ total emissions. Correlation ≠ causation.</p><button className="text-button" onClick={()=>nav('methodology')}>Explore the methodology <ArrowUpRight size={12}/></button></footer>
 </main></div>{run&&<div className="dialog-backdrop"><section ref={dialogRef} role="dialog" aria-modal="true" aria-label={`Ingestion run ${run}`} className="run-dialog"><header><h2>Ingestion run #{run}</h2><button className="icon-button" onClick={()=>setRun(null)} aria-label="Close run details"><X/></button></header>{detail.isPending?<p>Loading run…</p>:detail.isError?<p role="alert">Unable to retrieve run details.</p>:<DataTable rows={detail.data?.rows||[]}/>}<button className="button" onClick={()=>setRun(null)}>Close</button></section></div>}
 </div>
}
function Pagination({offset,sort,update}:{offset:number;sort:string;update:(v:Record<string,string>)=>void}){return <div className="pagination"><button className="button" disabled={!offset} onClick={()=>update({offset:String(Math.max(0,offset-500))})}>Previous 500</button><span>Rows {offset+1}–{offset+500}</span><button className="button" onClick={()=>update({offset:String(offset+500)})}>Next 500</button><button className="button" onClick={()=>update({sort:sort==='asc'?'desc':'asc',offset:'0'})}>{sort==='asc'?'Oldest first':'Newest first'} ↕</button></div>}
