'use strict';

const paths = {
  bolt: '<path d="m13 2-9 12h7l-1 8 10-12h-7l1-8Z"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  overview: '<rect x="3" y="3" width="7" height="10" rx="1.5"/><rect x="14" y="3" width="7" height="6" rx="1.5"/><rect x="14" y="13" width="7" height="8" rx="1.5"/><rect x="3" y="17" width="7" height="4" rx="1.5"/>',
  chart: '<path d="M3 3v18h18M6 15l4-5 4 3 6-8"/>',
  history: '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6m3-4v6l4 2"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
  leaf: '<path d="M20 3c-5 1-11-1-15 4-3 4-1 10 4 11 7 2 12-5 11-15Z"/><path d="M3 21c3-7 7-9 12-12"/>',
  settings: '<path d="m9 3-1 3-3 1-2 4 2 2 1 4 3 1 2 3 4-1 1-3 3-1 2-4-2-2-1-4-3-1-2-3-4 1Z"/><circle cx="12" cy="12" r="3"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2m4 0h2"/>',
  refresh: '<path d="M20 7a9 9 0 0 0-15-2L3 8m0-5v5h5m-4 9a9 9 0 0 0 15 2l2-3m0 5v-5h-5"/>',
  activity: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
  peak: '<path d="m3 17 6-8 4 4 8-10M15 3h6v6"/>',
  battery: '<rect x="2" y="6" width="18" height="12" rx="2"/><path d="M22 10v4M6 10v4m4-4v4m4-4v4"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  tower: '<path d="m8 3 8 0-1 4 5 14h-3l-5-7-5 7H4L9 7 8 3Zm-4 7h16M7 15h10M9 7h6M8 3l7 4m1-4L9 7"/>',
  building: '<rect x="4" y="7" width="16" height="14" rx="1"/><path d="M9 7V3h6v4M8 11h1m6 0h1m-8 4h1m6 0h1m-5 6v-3h2v3"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Zm-8 12h4"/>',
  shield: '<path d="m12 2 8 3v6c0 5-4 9-8 11-4-2-8-6-8-11V5l8-3Z"/><path d="m8 11 3 3 5-6"/>',
  'arrow-right': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  x: '<path d="m6 6 12 12M6 18 18 6"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  edit: '<path d="m16 3 5 5-12 12-6 1 1-6L16 3Zm-3 3 5 5"/>',
  file: '<path d="M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8m-8 4h6"/>',
  external: '<path d="M14 3h7v7m0-7L10 14M10 3H3v18h18v-7"/>',
  plug: '<path d="M9 3v5m6-5v5M7 8h10v4a5 5 0 0 1-10 0V8Zm5 9v5"/>',
  alert: '<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v.1"/>',
  chevrons: '<path d="m8 8 4-4 4 4m-8 8 4 4 4-4"/>'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.info}</svg>`;
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (n, digits = 1) => new Intl.NumberFormat('en', {maximumFractionDigits:digits, minimumFractionDigits:digits}).format(n);
const shortDate = stamp => new Date(stamp.replace(' ', 'T') + 'Z').toLocaleDateString('en-GB', {month:'short',day:'numeric',timeZone:'UTC'});
const fullDate = stamp => new Date(stamp.replace(' ', 'T') + 'Z').toLocaleDateString('en-GB', {month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const hourLabel = stamp => stamp.slice(11,16);
const datetimeUTC = (date, hours = 0) => new Date(new Date(date + 'Z').getTime() + hours * 3600000).toISOString().slice(0,19).replace('T',' ');
const sourceLabel = row => row.grid_mode === 'renewable_storage' ? 'Renewable storage' : 'Main grid';
const reasonLabels = {normal_demand:'Demand is at or below 160 kW, outside the evening window.',demand_threshold:'Demand exceeds 160 kW. Renewable storage is scheduled.',evening_window:'Evening window (18:00–22:00). Renewable storage is scheduled.',demand_and_evening:'Demand exceeds 160 kW and falls in the evening window.'};
const state = {run:null, health:null, selected:0, offset:9, view:'overview', filter:'all', busy:false, inputMode:'csv', draft:[], fileName:'', chartMode:'demand', scenario:null, officialSampleCSV:null};
document.querySelectorAll('[data-icon]').forEach(element => element.innerHTML = icon(element.dataset.icon));

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}
function showError(message, form = false) {
  const banner = $(form ? 'form-error' : 'error-banner');
  banner.textContent = message;
  banner.hidden = false;
}
function clearErrors() { $('error-banner').hidden = true; $('form-error').hidden = true; }
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4000); }
function setBusy(busy) {
  state.busy = busy;
  for (const id of ['run-forecast','next-sample','new-forecast']) $(id).disabled = busy;
  $('run-forecast').innerHTML = busy ? '<span class="spinner"></span>Generating forecast…' : icon('bolt') + 'Generate forecast';
  $('server-status').textContent = busy ? 'Forecast in progress' : 'Workspace ready';
}
async function createForecast(payload) {
  setBusy(true);
  clearErrors();
  try {
    const run = await api('/api/forecast', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    useRun(run);
    return run;
  } finally { setBusy(false); }
}
function useRun(run) {
  state.run = run;
  state.officialSampleCSV=run.input_source==='official_sample'?rowsCSV(run.rows):null;
  state.selected = 0;
  $('loading-state').hidden = true;
  const live = run.provider === 'quickml';
  $('provider-badge').innerHTML = '<span class="status-dot"></span>' + (live ? 'QuickML forecast' : 'Local preview');
  $('provider-badge').classList.toggle('connected', live);
  $('window-label').textContent = `${fullDate(run.window_start)} · ${hourLabel(run.window_start)}–${hourLabel(run.window_end)}` + (run.window_start.slice(0,10) !== run.window_end.slice(0,10) ? ' (+1 day)' : '');
  $('sample-label').textContent = run.input_source==='official_sample'?'Official 2015 sample · 24 hourly rows':'Uploaded or manually entered telemetry';
  $('average-demand').textContent = number(run.summary.average_kw);
  $('total-energy').textContent = number(run.summary.total_kwh,0) + ' kWh';
  $('peak-demand').textContent = number(run.summary.peak_kw);
  $('peak-time').textContent = 'At ' + hourLabel(run.summary.peak_timestamp);
  const peak = $('peak-state');
  const peakDemand = Math.max(...run.rows.map(row => row.target_demand_kw));
  peak.textContent = peakDemand >= 200 ? 'Overload' : peakDemand > 160 ? 'Storage' : 'Within limits';
  peak.className = 'tiny-badge ' + (peakDemand >= 200 ? 'danger' : peakDemand > 160 ? 'warning' : 'success');
  $('storage-hours').textContent = run.summary.storage_hours;
  $('storage-energy').textContent = number(run.summary.storage_delivered_kwh,0) + ' kWh';
  $('ending-soc').textContent = number(run.summary.end_soc_pct,0);
  $('reserve-label').textContent = `${number(run.battery.reserve_pct,0)}% reserve`;
  $('schedule-summary').textContent = `${run.summary.main_grid_hours}h main grid · ${run.summary.storage_hours}h storage · ${run.summary.transitions} source transitions`;
  $('run-source-note').textContent = live ? 'Forecasts returned by the published QuickML endpoint. Battery state is simulated.' : `Local model: ${run.model_name||'earlier development model'} · Battery state is simulated.`;
  $('explorer-window').textContent = `${fullDate(run.window_start)} ${hourLabel(run.window_start)} → ${fullDate(run.window_end)} ${hourLabel(run.window_end)} · ${live ? 'QuickML' : 'Local preview'}`;
  $('hour-picker').innerHTML = run.rows.map((row,i) => `<option value="${i}">${hourLabel(row.timestamp)}</option>`).join('');
  document.querySelectorAll('.metric-spark').forEach((svg,index)=>{
    const values=run.rows.map(row=>index===3?row.battery_soc_pct:index===2?(row.grid_mode==='renewable_storage'?1:0):row.target_demand_kw);
    const low=Math.min(...values),high=Math.max(...values),range=high-low||1;
    const points=values.map((value,i)=>`${i*200/23},${27-(value-low)/range*23}`).join(' ');
    const color=['#8ed7b8','#b58a51','#398d70','#748eaf'][index];
    svg.innerHTML=`<polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`;
  });
  renderOperationalBanner();
  renderSchedule(); renderChart(); selectHour(0); renderInsights(); renderTable();
  renderSignals();if(state.health)renderModel();
  state.scenario = null;
  switchView('overview');
}
const views = {
  overview: ['Overview','Microgrid operations','Plan the next 24 hours with a clear view of demand, risk, and storage.'],
  forecast: ['Forecast explorer','Forecast explorer','Follow each hour from weather inputs to a power-source decision.'],
  scenario: ['Scenario lab','Plan for a different outcome','Test storage capacity and battery assumptions before committing to a dispatch plan.'],
  history: ['Run history','Your forecast history','A record of the forecasts you’ve explored in this browser.'],
  model: ['Model & connection','Behind the forecast','Understand the model, explore its results, and connect QuickML.']
};
function switchView(view) {
  if (!views[view]) return;
  state.view = view;
  for (const key of Object.keys(views)) $(key + '-view').hidden = key !== view || (!state.run && (key === 'overview' || key === 'forecast'));
  document.querySelectorAll('.nav-item').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
  });
  $('breadcrumb-title').textContent = views[view][0];
  $('page-title').innerHTML = escapeHTML(views[view][1]) + '<span class="title-dot">.</span>';
  $('page-subtitle').textContent = views[view][2];
  if (view === 'history') renderHistory();
  if (view === 'scenario') initializeScenario();
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => switchView(button.dataset.view)));
$('connection-button').addEventListener('click', () => switchView('model'));

function renderSchedule() {
  $('hour-schedule').innerHTML = state.run.rows.map((row,i) => `<button class="hour-button ${row.grid_mode === 'renewable_storage' ? 'storage' : ''} ${row.critical_overload ? 'overload' : ''}" data-hour="${i}" aria-label="${escapeHTML(row.timestamp)}, ${number(row.target_demand_kw)} kilowatts, ${sourceLabel(row)}${row.critical_overload ? ', critical overload' : ''}" aria-pressed="false"><span class="hour-bar"></span><small>${hourLabel(row.timestamp)}</small></button>`).join('');
  $('hour-schedule').querySelectorAll('button').forEach(button => button.addEventListener('click', () => selectHour(Number(button.dataset.hour))));
}
function selectHour(index) {
  if (!state.run) return;
  state.selected = index;
  $('hour-picker').value = String(index);
  const row = state.run.rows[index];
  const storage = row.grid_mode === 'renewable_storage';
  $('selected-hour-label').textContent = `${shortDate(row.timestamp)} · ${hourLabel(row.timestamp)}`;
  $('dispatch-state-label').textContent = storage ? 'Renewable Storage Mode' : 'Main Grid Mode';
  $('dispatch-state').classList.toggle('storage', storage);
  $('grid-node').classList.toggle('active', !storage);
  $('battery-node').classList.toggle('storage-active', storage);
  $('grid-line').classList.toggle('active', !storage);
  $('battery-line').classList.toggle('storage-active', storage);
  $('grid-node-detail').textContent = storage ? 'Standby' : 'Supplying load';
  $('battery-node-detail').textContent = storage ? `${number(row.battery_discharge_kw)} kW output` : `${number(row.battery_charge_kw)} kW charging`;
  $('selected-load').textContent = `${number(row.target_demand_kw)} kW forecast demand`;
  $('selected-soc').textContent = number(row.battery_soc_pct,0) + '%';
  $('soc-fill').style.width = row.battery_soc_pct + '%';
  $('soc-reserve').style.left = state.run.battery.reserve_pct + '%';
  $('dispatch-reason').textContent = row.storage_shortfall_kwh > 0 ? `${reasonLabels[row.reason]} Battery shortfall: ${number(row.storage_shortfall_kwh)} kWh.` : reasonLabels[row.reason];
  document.querySelectorAll('.hour-button').forEach((button,i) => {button.classList.toggle('selected',i === index);button.setAttribute('aria-pressed',String(i === index));});
  const marker = $('selected-chart-marker');
  if (marker) {
    const {x,y} = chartPoint(index);
    marker.setAttribute('cx',x); marker.setAttribute('cy',y);
    $('selected-chart-line').setAttribute('x1',x); $('selected-chart-line').setAttribute('x2',x);
  }
}
function chartPoint(index) {
  const rows=state.run.rows;
  const max=state.chartMode==='battery'?100:Math.max(250,Math.ceil(Math.max(...rows.map(row=>row.upper_demand_kw??row.target_demand_kw))/50)*50);
  const value=state.chartMode==='battery'?rows[index].battery_soc_pct:rows[index].target_demand_kw;
  return {x:51+index*728/23,y:247-value/max*220,max};
}
function renderChart() {
  if(!state.run)return;
  const rows=state.run.rows;
  const battery=state.chartMode==='battery';
  const points=rows.map((_,i)=>chartPoint(i));
  const max=points[0].max;
  const linePath=points.map((point,i)=>`${i?'L':'M'}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ');
  const uncertainty=state.run.diagnostics?.uncertainty;
  $('chart-legend').innerHTML=`<span><i class="legend-dot demand-dot"></i>${battery?'Simulated charge':'Predicted demand'}</span><span><i class="legend-dash"></i>${battery?'Protected reserve':'Storage threshold'}</span><span><i class="legend-box"></i>Evening window</span><span class="chart-unit" id="chart-unit">${battery?'SOC %':'kW'}</span>`;
  $('band-label').textContent=battery?'Battery simulation':uncertainty?'90% residual reference band':'No live uncertainty estimate';
  $('chart-note').textContent=battery?'Projected battery charge, with the protected reserve shown as a dashed line.':uncertainty?`Shaded band: historical residual reference. Backtest coverage ${number(uncertainty.heldout_coverage_pct,1)}%; future coverage is not guaranteed.`:'Point forecast from QuickML. No calibrated uncertainty band has been supplied for this endpoint.';
  let svg=`<defs><linearGradient id="demand-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#3c9678" stop-opacity=".22"/><stop offset="100%" stop-color="#3c9678" stop-opacity=".015"/></linearGradient></defs><title>${battery?'Battery state of charge':'24-hour demand forecast'}</title><desc>${battery?'Charge is simulated under the configured battery limits.':'Demand and empirical residual reference band, with fixed 160 and 200 kilowatt thresholds.'}</desc>`;
  for(let tick=0;tick<=max;tick+=battery?20:50){const y=247-tick/max*220;svg+=`<line x1="51" y1="${y}" x2="779" y2="${y}" stroke="#eaf0e9"/><text x="37" y="${y+4}" text-anchor="end">${tick}${battery?'%':''}</text>`;}
  rows.forEach((row,i)=>{const hour=Number(row.timestamp.slice(11,13));if(hour>=18&&hour<=22){const left=Math.max(51,points[i].x-728/46);svg+=`<rect x="${left}" y="27" width="${Math.min(779-left,728/23)}" height="220" fill="#faf2df" opacity=".7"/>`;}});
  if(!battery&&uncertainty&&rows.every(row=>row.lower_demand_kw!=null)){
    const band=[...rows.map((r,i)=>`${points[i].x},${247-r.upper_demand_kw/max*220}`),...rows.map((r,i)=>`${points[i].x},${247-r.lower_demand_kw/max*220}`).reverse()].join(' ');
    svg+=`<polygon points="${band}" fill="#dcece5" opacity=".8"/>`;
  }else svg+=`<path d="${linePath} L779,247 L51,247 Z" fill="url(#demand-fill)"/>`;
  if(battery){const y=247-state.run.battery.reserve_pct/100*220;svg+=`<line x1="51" y1="${y}" x2="779" y2="${y}" stroke="#b6aa86" stroke-dasharray="5 5"/><text x="775" y="${y-8}" text-anchor="end">${state.run.battery.reserve_pct}% reserve</text>`;}
  else{
    for(const [value,color,label]of [[160,'#8ba697','160 · storage'],[200,'#caa778','200 · overload']]){const y=247-value/max*220;svg+=`<line x1="51" y1="${y}" x2="779" y2="${y}" stroke="${color}" stroke-dasharray="5 5"/><text x="775" y="${y-7}" text-anchor="end">${label}</text>`;}
  }
  svg+=`<path d="${linePath}" fill="none" stroke="#247e6a" stroke-width="2.7" stroke-linejoin="round" stroke-linecap="round"/>`;
  rows.forEach((row,i)=>{if(i%3===0||i===23)svg+=`<text x="${points[i].x}" y="272" text-anchor="middle">${hourLabel(row.timestamp)}</text>`;});
  const selected=points[state.selected];
  svg+=`<line id="selected-chart-line" x1="${selected.x}" x2="${selected.x}" y1="27" y2="247" stroke="#a8c5b6" stroke-dasharray="3 4"/><circle id="selected-chart-marker" cx="${selected.x}" cy="${selected.y}" r="4.5" fill="#247e6a" stroke="white" stroke-width="2"/>`;
  points.forEach((point,i)=>{svg+=`<rect data-point="${i}" x="${Math.max(51,point.x-728/46)}" y="20" width="${728/23}" height="230" fill="transparent"/>`;});
  $('demand-chart').innerHTML=svg;
  $('demand-chart').setAttribute('aria-label',battery?'Simulated 24-hour battery charge':state.run.provider==='quickml'?'24-hour QuickML demand point forecast':'24-hour demand forecast and empirical uncertainty band');
  $('demand-chart').querySelectorAll('[data-point]').forEach(rect=>{rect.addEventListener('pointerenter',()=>showChartTooltip(Number(rect.dataset.point)));rect.addEventListener('click',()=>selectHour(Number(rect.dataset.point)));});
  $('demand-chart').onpointerleave=()=>{$('chart-tooltip').hidden=true;};
}
function showChartTooltip(index) {
  const row=state.run.rows[index], battery=state.chartMode==='battery';
  const tooltip=$('chart-tooltip');
  tooltip.innerHTML=`<small>${shortDate(row.timestamp)} · ${hourLabel(row.timestamp)}</small><strong>${number(battery?row.battery_soc_pct:row.target_demand_kw)} ${battery?'% SOC':'kW'}</strong>${!battery&&row.lower_demand_kw!=null?`<small>${number(row.lower_demand_kw)}–${number(row.upper_demand_kw)} kW reference band</small><br>`:''}<small>${sourceLabel(row)}${row.critical_overload?' · Overload':''}</small>`;
  tooltip.hidden=false;
  const container=$('chart-container'),{x,y}=chartPoint(index),width=container.clientWidth-36;
  tooltip.style.left=Math.max(8,Math.min(container.clientWidth-tooltip.offsetWidth-8,18+x/800*width-tooltip.offsetWidth/2))+'px';
  tooltip.style.top=Math.max(8,y/800*width-tooltip.offsetHeight)+'px';
}
function insight(iconName,title,body,tone='',aside='') {
  return `<div class="insight"><span class="insight-icon ${tone}">${icon(iconName)}</span><div><h3>${escapeHTML(title)}</h3><p>${escapeHTML(body)}</p></div>${aside?`<span class="insight-time">${escapeHTML(aside)}</span>`:''}</div>`;
}
function renderInsights() {
  const run=state.run, summary=run.summary;
  const critical=run.rows.filter(row=>row.critical_overload);
  const items=[];
  if(critical.length)items.push(insight('alert',`Critical overload forecast in ${critical.length} hour${critical.length===1?'':'s'}`,`Demand reaches ${number(summary.peak_kw)} kW. Review the affected hours before dispatch.`,'warning','≥ 200 kW'));
  else items.push(insight('shield','Demand stays below the overload limit','No forecast hour reaches the critical 200 kW threshold.','green'));
  const evening=run.rows.filter(row=>Number(row.timestamp.slice(11,13))>=18&&Number(row.timestamp.slice(11,13))<=22);
  items.push(insight('leaf','Evening storage window is scheduled',`${evening.length} evening hours use renewable storage. This rule applies independently of demand.`,'green','18:00–22:00'));
  if(summary.storage_shortfall_kwh>0)items.push(insight('battery','Battery capacity needs attention',`${number(summary.storage_shortfall_kwh)} kWh of planned storage demand cannot be served with these settings. Increase capacity or available charge.`,'danger','Simulation'));
  else items.push(insight('battery','Battery covers the planned storage load',`Simulated charge ends at ${number(summary.end_soc_pct,0)}%, with a ${number(run.battery.reserve_pct,0)}% protected reserve.`,'','Simulation'));
  if(run.diagnostics?.threshold_watch_hours)items.push(insight('activity',`${run.diagnostics.threshold_watch_hours} hour${run.diagnostics.threshold_watch_hours===1?'':'s'} near the overload threshold`,'The point forecast is below 200 kW, but its historical residual band crosses the limit.','warning','Forecast uncertainty'));
  if(run.diagnostics?.out_of_training_range_hours)items.push(insight('info','Weather inputs extend beyond the training range',`${run.diagnostics.out_of_training_range_hours} forecast hours contain at least one weather value outside the observed training minimum or maximum.`,'warning','Data range'));
  if(run.warnings.length)items.push(insight('info',`${run.warnings.length} missing weather value${run.warnings.length===1?'':'s'} filled`,run.warnings.slice(0,2).join(' '),'warning','Data cleanup'));
  $('insights-list').innerHTML=items.join('');
  $('alert-count').textContent=items.length;
}
function renderTable() {
  if(!state.run)return;
  const rows=state.run.rows.filter(row=>state.filter==='all'||state.filter==='storage'&&row.grid_mode==='renewable_storage'||state.filter==='alerts'&&row.critical_overload);
  $('forecast-table').innerHTML=rows.length?rows.map(row=>`<tr><td>${shortDate(row.timestamp)} · ${hourLabel(row.timestamp)}</td><td>${number(row.ambient_temp_c)} °C</td><td>${number(row.humidity_pct,0)}%</td><td>${number(row.solar_irradiance_wm2,0)}</td><td><strong>${number(row.target_demand_kw)} kW</strong></td><td><span class="source-pill ${row.grid_mode==='renewable_storage'?'storage':''}"><span class="mini-dot"></span>${sourceLabel(row)}</span></td><td>${number(row.battery_soc_pct)}%</td><td>${row.critical_overload?'<span class="tiny-badge danger">Critical overload</span>':row.storage_shortfall_kwh>0?'<span class="tiny-badge warning">Storage shortfall</span>':'<span class="tiny-badge success">Within limits</span>'}${row.critical_overload&&row.storage_shortfall_kwh>0?' <span class="tiny-badge warning">Shortfall</span>':''}</td></tr>`).join(''):'<tr><td colspan="8" class="empty-state">No forecast hours match this filter.</td></tr>';
  $('row-count').textContent=`${rows.length} of 24 forecast hours`;
}
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{state.filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('selected',b===button));renderTable();}));
function exportForecast() {
  if(!state.run)return;
  const link=document.createElement('a');link.href=`/api/runs/${state.run.id}/export`;link.download='gridlens-forecast.csv';link.click();
}
$('export-forecast').addEventListener('click',exportForecast);
$('export-explorer').addEventListener('click',exportForecast);
function renderSignals() {
  const labels={transition:'Source transition',critical_overload:'Critical overload',storage_shortfall:'Storage shortfall'};
  $('signal-table').innerHTML=state.run.events.map(event=>{
    const detail=event.kind==='transition'?`${event.mode==='renewable_storage'?'Renewable storage':'Main grid'} · ${reasonLabels[event.reason]}`:event.kind==='critical_overload'?`${number(event.demand_kw)} kW demand · independent ≥ 200 kW alert`:`${number(event.shortfall_kwh)} kWh cannot be served by the simulated battery`;
    return `<tr><td>${escapeHTML(hourLabel(event.timestamp))}</td><td><span class="tiny-badge ${event.kind==='critical_overload'?'danger':event.kind==='transition'?'success':'warning'}">${escapeHTML(labels[event.kind]||event.kind)}</span></td><td>${escapeHTML(detail)}</td></tr>`;
  }).join('');
}
$('export-signals').addEventListener('click',()=>{if(!state.run)return;const link=document.createElement('a');link.href=`/api/runs/${state.run.id}/signals`;link.download='gridlens-control-signals.json';link.click();});

async function renderHistory() {
  $('history-list').innerHTML='<div class="empty-state">Loading your previous forecasts…</div>';
  try {
    const {runs}=await api('/api/history');
    $('history-list').innerHTML=runs.length?runs.map(run=>`<button class="history-item" data-run="${escapeHTML(run.id)}"><span class="history-icon">${icon('chart')}</span><span class="history-info"><strong>${fullDate(run.window_start)} · ${hourLabel(run.window_start)}–${hourLabel(run.window_end)}</strong><small>${run.provider==='quickml'?'QuickML endpoint':'Local preview'} · Run ${new Date(run.created_at).toLocaleString('en-GB',{dateStyle:'medium',timeStyle:'short'})}</small></span><span class="history-stats"><span>${number(run.summary.peak_kw)} kW<small>Peak demand</small></span><span>${run.summary.storage_hours} hours<small>Storage dispatch</small></span></span>${icon('arrow-right')}</button>`).join(''):'<div class="empty-state">No forecasts yet. Create a forecast to start your history.</div>';
    $('history-list').querySelectorAll('[data-run]').forEach(button=>button.addEventListener('click',async()=>{try{const run=await api('/api/runs/'+button.dataset.run);useRun(run);toast('Previous forecast restored.');}catch(error){showError(error.message);}}));
  } catch(error) { $('history-list').innerHTML=`<div class="empty-state">${escapeHTML(error.message)}</div>`; }
}
$('refresh-history').addEventListener('click',renderHistory);
function renderModel() {
  const health=state.health;
  const cloud=health.quickml_configured&&health.quickml_model;
  $('model-card-title').textContent=cloud?'Published QuickML model':'Selected local model';
  $('model-rmse').innerHTML=number(cloud?cloud.metrics.root_mean_squared_error:health.local_model.validation.rmse_kw,2)+'<span> kW</span>';
  $('model-mae').innerHTML=number(cloud?cloud.metrics.mean_absolute_error:health.local_model.validation.mae_kw,2)+'<span> kW</span>';
  $('model-rows').textContent=number(cloud?cloud.training_rows:health.local_model.training_rows,0);
  $('model-name').textContent=cloud?`${cloud.algorithm} · Zoho Catalyst QuickML`:health.local_model.name;
  const benchmark=health.local_model.benchmark;
  if(benchmark){
    const max=Math.max(...benchmark.candidates.map(item=>item.cv_rmse_kw));
    $('benchmark-table').innerHTML=benchmark.candidates.map(item=>`<div class="benchmark-row ${item.kind===benchmark.selected?'selected':''}"><strong>${escapeHTML(item.name)}${item.kind===benchmark.selected?'<span class="tiny-badge success">Selected</span>':''}</strong><div class="benchmark-bar"><span></span></div><span class="benchmark-value">${number(item.cv_rmse_kw,2)} kW</span></div>`).join('')+`<p class="benchmark-caption">Rolling-origin RMSE, lower is better. ${escapeHTML(benchmark.selection_policy)}. Separate later-period development RMSE: ${number(benchmark.validation.rmse_kw,2)} kW.</p>`;
    // Set dynamic bar widths using the DOM instead of CSP-blocked inline markup.
    $('benchmark-table').querySelectorAll('.benchmark-bar span').forEach((bar,i)=>bar.style.width=benchmark.candidates[i].cv_rmse_kw/max*100+'%');
    const u=benchmark.uncertainty;
    $('uncertainty-explanation').textContent=`Uncertainty reference: ±${number(u.radius_kw,1)} kW from ${u.calibration_rows} later calibration rows; ${number(u.heldout_coverage_pct,1)}% empirical coverage on the 800-row development holdout. This is a residual reference band, not a guaranteed future coverage claim.`;
    $('validation-description').textContent=`${number(health.local_model.validation.rmse_kw,2)} kW RMSE on the final 800 labeled rows, after selection on earlier chronological folds. Final inference model is refitted on all 4,000 labeled rows. These are development results, not QuickML or hidden-test scores.`;
  }
  if(cloud)$('validation-description').textContent=`QuickML's built-in evaluation: R² ${number(cloud.metrics.r2_score,3)}, RMSE ${number(cloud.metrics.root_mean_squared_error,2)} kW. These are cloud validation metrics, not a hidden-test score or the local chronological benchmark below.`;
  $('history-storage-note').textContent=health.history_storage==='catalyst_datastore'?'Forecasts are saved in Catalyst Data Store and remain available after cloud restarts. Access is limited to this browser session.':'Local development history uses SQLite on this server.';

  $('quickml-state').textContent=health.quickml_configured?'Credentials present':'Not configured';
  $('quickml-state').classList.toggle('warning',!health.quickml_configured);
  if(health.quickml_configured){$('connection-title').textContent='Ready for a connection test';$('connection-description').textContent='Credentials are present on the server. Select QuickML and run a forecast to verify the published endpoint.';}
  if(health.quickml_configured&&state.run?.provider==='quickml'){$('quickml-state').textContent='QuickML forecast verified';$('connection-title').textContent='Published model in use';$('connection-description').textContent='The displayed forecast was returned by the published QuickML endpoint. Its inputs, dispatch signals and battery simulation are available for inspection and export.';}
}

function rowsCSV(rows) {return 'timestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2\n'+rows.map(row=>[row.timestamp,row.ambient_temp_c,row.humidity_pct,row.solar_irradiance_wm2].join(',')).join('\n');}
function parseDraftCSV(text) {
  // Quoted CSV fields and CRLF are supported; authoritative validation is server-side.
  const lines=[];let row=[],cell='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const char=text[i];
    if(char==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(char===','&&!quoted){row.push(cell);cell='';}
    else if((char==='\n'||char==='\r')&&!quoted){row.push(cell);if(row.some(value=>value.trim()))lines.push(row);row=[];cell='';if(char==='\r'&&text[i+1]==='\n')i++;}
    else cell+=char;
  }
  if(quoted)throw new Error('A CSV field has an unclosed quote. Correct it before editing hourly inputs.');
  row.push(cell);if(row.some(value=>value.trim()))lines.push(row);
  const headers=lines.shift()||[];
  const required=['timestamp','ambient_temp_c','humidity_pct','solar_irradiance_wm2'];
  if(required.some(key=>!headers.includes(key)))throw new Error('The CSV needs timestamp and all three weather columns.');
  if(lines.length!==24)throw new Error(`Use exactly 24 telemetry rows before editing hourly inputs; received ${lines.length}.`);
  return lines.map(values=>Object.fromEntries(required.map(key=>[key,values[headers.indexOf(key)]??''])));
}
function populateDraft(rows) {
  state.draft=rows.map(row=>({...row}));
  $('csv-text').value=rowsCSV(rows);
  $('manual-start').value=rows[0].timestamp.replace(' ','T').slice(0,16);
  renderManual();
}
function renderManual() {
  const disabled=state.inputMode!=='manual'?' disabled':'';
  const cols=[['ambient_temp_c',-60,65],['humidity_pct',0,100],['solar_irradiance_wm2',0,1500]];
  $('manual-rows').innerHTML=state.draft.map((row,i)=>`<tr><td>${hourLabel(row.timestamp)}</td>${cols.map(([key,min,max])=>`<td><input data-row="${i}" data-column="${key}" type="number" step="any" min="${min}" max="${max}" value="${escapeHTML(row[key]??'')}" aria-label="${escapeHTML(key)} at ${hourLabel(row.timestamp)}"${disabled}></td>`).join('')}</tr>`).join('');
  $('manual-rows').querySelectorAll('input').forEach(input=>input.addEventListener('input',()=>state.draft[Number(input.dataset.row)][input.dataset.column]=input.value));
}
function setInputMode(mode) {
  state.inputMode=mode;
  const manual=mode==='manual';
  $('csv-input-panel').hidden=manual;$('manual-input-panel').hidden=!manual;
  $('csv-tab').classList.toggle('selected',!manual);$('manual-tab').classList.toggle('selected',manual);
  $('csv-tab').setAttribute('aria-selected',String(!manual));$('manual-tab').setAttribute('aria-selected',String(manual));
  $('manual-start').disabled=!manual;
  renderManual();
}
function openForecast() {
  if(state.busy)return;
  clearErrors();
  if(state.run){populateDraft(state.run.rows);const b=state.run.battery;for(const [id,key]of [['capacity','capacity_kwh'],['initial','initial_soc_pct'],['reserve','reserve_pct'],['charge','charge_kw'],['discharge','max_discharge_kw']])$('battery-'+id).value=b[key];$('battery-efficiency').value=Math.round(b.efficiency*100);}
  $('provider-select').value=state.health?.quickml_configured?'quickml':'local_preview';
  $('provider-select').dispatchEvent(new Event('change'));
  $('file-label').textContent='Choose a CSV or drop it here';$('csv-file').value='';state.fileName='';
  setInputMode('csv');
  $('forecast-dialog').showModal();
}
$('new-forecast').addEventListener('click',openForecast);
$('close-dialog').addEventListener('click',()=>$('forecast-dialog').close());
$('forecast-dialog').addEventListener('click',event=>{if(event.target===$('forecast-dialog')){const rect=$('forecast-dialog').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('forecast-dialog').close();}});
$('csv-tab').addEventListener('click',()=>{if(state.inputMode==='manual')$('csv-text').value=rowsCSV(state.draft);setInputMode('csv');});
$('manual-tab').addEventListener('click',()=>{
  try{if(state.inputMode==='csv'){const rows=parseDraftCSV($('csv-text').value);populateDraft(rows);}$('form-error').hidden=true;setInputMode('manual');}
  catch(error){showError(error.message,true);}
});
for(const [id,other] of [['csv-tab','manual-tab'],['manual-tab','csv-tab']])$(id).addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();$(other).click();$(other).focus();}});
$('manual-start').addEventListener('change',()=>{
  const start=$('manual-start').value;
  if(!start||!/^\d{4}-\d\d-\d\dT\d\d:00$/.test(start))return;
  state.draft=state.draft.map((row,i)=>({...row,timestamp:datetimeUTC(start+':00',i)}));renderManual();
});
async function loadFile(file) {
  if(!file)return;
  if(file.size>1_000_000){showError('Choose a CSV smaller than 1 MB.',true);return;}
  try{$('csv-text').value=await file.text();$('file-label').textContent=file.name;state.fileName=file.name;$('form-error').hidden=true;}
  catch{showError('The selected file could not be read. Try pasting its CSV contents.',true);}
}
$('csv-file').addEventListener('change',event=>loadFile(event.target.files[0]));
$('upload-zone').addEventListener('dragover',event=>{event.preventDefault();$('upload-zone').classList.add('dragging');});
$('upload-zone').addEventListener('dragleave',()=>$('upload-zone').classList.remove('dragging'));
$('upload-zone').addEventListener('drop',event=>{event.preventDefault();$('upload-zone').classList.remove('dragging');loadFile(event.dataTransfer.files[0]);});
$('use-sample').addEventListener('click',async()=>{try{const data=await api('/api/sample?offset='+state.offset);populateDraft(data.rows);state.officialSampleCSV=rowsCSV(data.rows);$('file-label').textContent='Official sample telemetry loaded';toast('24 official sample rows are ready.');}catch(error){showError(error.message,true);}});
$('provider-select').addEventListener('change',()=>{$('engine-help').textContent=$('provider-select').value==='quickml'?(state.health?.quickml_configured?'Live inference uses the published QuickML endpoint. Requests can take a few minutes.':'QuickML credentials are not configured yet. Follow Model & connection before a live run.'):'Local forecasts use the supplied historical data model. QuickML is required for final submission.';});
$('forecast-form').addEventListener('invalid',event=>{const detail=event.target.closest('details');if(detail)detail.open=true;},true);
$('forecast-form').addEventListener('submit',async event=>{
  event.preventDefault();if(state.busy)return;
  const battery={capacity_kwh:Number($('battery-capacity').value),initial_soc_pct:Number($('battery-initial').value),reserve_pct:Number($('battery-reserve').value),charge_kw:Number($('battery-charge').value),max_discharge_kw:Number($('battery-discharge').value),efficiency:Number($('battery-efficiency').value)/100};
  const draftCSV=state.inputMode==='csv'?$('csv-text').value:rowsCSV(state.draft);
  const payload={provider:$('provider-select').value,battery,input_source:state.officialSampleCSV&&draftCSV===state.officialSampleCSV?'official_sample':'user_input'};
  if(state.inputMode==='csv'){if(!$('csv-text').value.trim()){showError('Upload a CSV, paste telemetry, or choose the official sample.',true);return;}payload.csv=$('csv-text').value;}
  else payload.rows=state.draft;
  try{const run=await createForecast(payload);$('forecast-dialog').close();toast(run.provider==='quickml'?'Live QuickML forecast generated.':'24-hour local preview forecast generated.');}
  catch(error){showError(error.message,true);}
});
$('next-sample').addEventListener('click',async()=>{
  try{state.offset=state.offset+24>976?9:state.offset+24;const sample=await api('/api/sample?offset='+state.offset);await createForecast({rows:sample.rows,provider:state.run?.provider||'local_preview',input_source:'official_sample',battery:state.run?.battery});toast('Loaded the next historical sample day.');}
  catch(error){showError(error.message);}
});
function renderOperationalBanner() {
  const summary=state.run.summary;
  const critical=summary.critical_hours, shortfall=summary.storage_shortfall_kwh;
  const banner=$('operational-banner');
  banner.classList.toggle('healthy',!critical&&shortfall<=0);
  banner.innerHTML=icon(critical||shortfall>0?'alert':'shield')+`<span><strong>${critical?`${critical} overload hours forecast`:shortfall>0?'Storage capacity needs attention':'The forecast is within operating limits'}</strong>${shortfall>0?` · ${number(shortfall,0)} kWh of storage demand cannot be served under the current battery plan.`:critical?' · Inspect the affected hours before dispatch.':' · No critical overload or storage shortfall in this window.'}</span><button class="text-button" id="review-plan">${shortfall>0?'Test battery capacity':'Inspect forecast'}${icon('arrow-right')}</button>`;
  $('review-plan').addEventListener('click',()=>switchView(shortfall>0?'scenario':'forecast'));
}
$('hour-picker').addEventListener('change',()=>selectHour(Number($('hour-picker').value)));
document.querySelectorAll('[data-chart-mode]').forEach(button=>button.addEventListener('click',()=>{
  state.chartMode=button.dataset.chartMode;
  document.querySelectorAll('[data-chart-mode]').forEach(item=>item.classList.toggle('selected',item===button));
  $('chart-tooltip').hidden=true;renderChart();
}));
function updateScenarioLabels() {
  $('scenario-capacity-value').textContent=number(Number($('scenario-capacity').value),0)+' kWh';
  $('scenario-initial-value').textContent=$('scenario-initial').value+'%';
}
$('scenario-capacity').addEventListener('input',updateScenarioLabels);
$('scenario-initial').addEventListener('input',updateScenarioLabels);
function initializeScenario() {
  if(!state.run)return;
  const config=state.scenario?.battery||state.run.battery;
  $('scenario-capacity').max=Math.max(20000,Math.ceil(config.capacity_kwh/250)*250);
  $('scenario-capacity').value=config.capacity_kwh;
  $('scenario-initial').value=config.initial_soc_pct;
  $('scenario-reserve').value=config.reserve_pct;
  $('scenario-charge').value=config.charge_kw;
  $('scenario-discharge').value=config.max_discharge_kw;
  $('scenario-efficiency').value=Math.round(config.efficiency*100);
  updateScenarioLabels();renderScenario(state.scenario);
}
function renderScenario(scenario) {
  const run=state.run, rows=scenario?.rows||run.rows;
  const current=run.rows;
  let svg='<title>Battery state: current plan versus scenario</title><desc>Comparison of simulated charge, with percentage units and one-hour steps.</desc>';
  for(let tick=0;tick<=100;tick+=20){const y=235-tick/100*210;svg+=`<line x1="51" y1="${y}" x2="779" y2="${y}" stroke="#e8eee6"/><text x="37" y="${y+4}" text-anchor="end">${tick}%</text>`;}
  const line=data=>data.map((row,i)=>`${i?'L':'M'}${51+i*728/23},${235-row.battery_soc_pct/100*210}`).join(' ');
  svg+=`<path d="${line(current)}" fill="none" stroke="#7796b2" stroke-width="2.5" ${scenario?'stroke-dasharray="5 4"':''}/>`;
  if(scenario)svg+=`<path d="${line(rows)}" fill="none" stroke="#247e6a" stroke-width="2.8"/>`;
  const reserve=scenario?.battery.reserve_pct??run.battery.reserve_pct,y=235-reserve/100*210;
  svg+=`<line x1="51" y1="${y}" x2="779" y2="${y}" stroke="#c3b58b" stroke-dasharray="3 5"/>`;
  rows.forEach((row,i)=>{if(i%4===0||i===23)svg+=`<text x="${51+i*728/23}" y="264" text-anchor="middle">${hourLabel(row.timestamp)}</text>`;});
  $('scenario-chart').innerHTML=svg;
  const summary=scenario?.summary||run.summary, base=run.summary;
  $('scenario-comparison').innerHTML=[
    ['Storage shortfall',number(summary.storage_shortfall_kwh,0)+' kWh',`Current: ${number(base.storage_shortfall_kwh,0)} kWh`],
    ['Ending charge',number(summary.end_soc_pct,0)+'%',`Current: ${number(base.end_soc_pct,0)}%`],
    ['Planned load served',number((1-summary.storage_shortfall_kwh/Math.max(summary.total_kwh,1))*100,1)+'%',`Demand: ${number(summary.total_kwh,0)} kWh`]
  ].map(([label,value,note])=>`<div><small>${label}</small><strong>${value}</strong><span>${note}</span></div>`).join('');
  const advice=scenario?.capacity_advice||run.capacity_advice;
  if(!advice){$('capacity-recommendation').innerHTML=icon('info')+'<p>Re-run this older forecast to calculate a capacity estimate.</p>';return;}
  $('capacity-recommendation').innerHTML=icon('battery')+`<div><h3>${advice.minimum_capacity_kwh!=null?`Estimated minimum: ${number(advice.minimum_capacity_kwh,0)} kWh`:'Charging assumptions cannot serve the storage schedule'}</h3><p>${advice.minimum_capacity_kwh!=null?`Capacity needed for this forecast with the selected starting charge, reserve, charging rate, and efficiency.`:'Increase initial charge or available charging. Scaling capacity alone cannot resolve this scenario.'} Required discharge capability: <strong>${number(advice.required_discharge_kw,1)} kW</strong>. ${advice.power_limit_insufficient?'The configured power limit is insufficient; increasing capacity alone will not fix it.':''}</p></div>`;
}
$('use-recommended').addEventListener('click',()=>{
  const advice=state.scenario?.capacity_advice||state.run?.capacity_advice;
  if(!advice?.minimum_capacity_kwh){$('scenario-error').textContent='A capacity estimate is unavailable. Review the initial charge and charging assumptions.';$('scenario-error').hidden=false;return;}
  const capacity=Math.ceil(advice.minimum_capacity_kwh/250)*250;
  $('scenario-capacity').max=Math.max(20000,capacity);$('scenario-capacity').value=capacity;
  $('scenario-discharge').value=Math.max(Number($('scenario-discharge').value),Math.ceil(advice.required_discharge_kw));
  updateScenarioLabels();$('scenario-form').requestSubmit();
});
$('scenario-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!state.run)return;
  $('scenario-error').hidden=true;$('simulate-scenario').disabled=true;
  const battery={capacity_kwh:Number($('scenario-capacity').value),initial_soc_pct:Number($('scenario-initial').value),reserve_pct:Number($('scenario-reserve').value),charge_kw:Number($('scenario-charge').value),max_discharge_kw:Number($('scenario-discharge').value),efficiency:Number($('scenario-efficiency').value)/100};
  try{const result=await api('/api/scenario',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:state.run.id,battery})});state.scenario=result;renderScenario(result);toast('Scenario calculated. Original forecast and dispatch rules are unchanged.');}
  catch(error){$('scenario-error').textContent=error.message;$('scenario-error').hidden=false;}
  finally{$('simulate-scenario').disabled=false;}
});
async function start() {
  setBusy(true);
  try{
    const [health,sample]=await Promise.all([api('/api/health'),api('/api/sample?offset='+state.offset)]);
    state.health=health;renderModel();populateDraft(sample.rows);
    const history=await api('/api/history');
    if(history.runs.length){const restored=await api('/api/runs/'+history.runs[0].id);useRun(restored);populateDraft(restored.rows);}
    else await createForecast({rows:sample.rows,provider:health.quickml_configured?'quickml':'local_preview',input_source:'official_sample'});
  }catch(error){$('loading-state').hidden=true;showError(error.message);$('server-status').textContent='Connection needs attention';}
  finally{setBusy(false);if(!state.run)$('server-status').textContent='Connection needs attention';}
}
start();
