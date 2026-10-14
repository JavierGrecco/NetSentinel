  const $ = (id) => document.getElementById(id);
  const state = { devices: [], events: [], scans: [] };
  function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function dateTime(value) { if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.getTime()) ? value : d.toLocaleString(); }
  function toast(message) { const el=$('toast'); el.textContent=message; el.hidden=false; window.clearTimeout(toast.timer); toast.timer=window.setTimeout(()=>el.hidden=true,4200); }
  function latestLocalAddresses() { const scan=state.scans.find(item=>(item.discovery?.networks||[]).length); return new Set((scan?.discovery?.networks||[]).map(network=>network.local_address).filter(Boolean)); }
  async function api(url, options={}) {
    let response;
    try {
      response=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});
    } catch {
      throw new Error('No se pudo contactar con el servidor local de NetSentinel. Código NS-CONN-001. Verificá que la aplicación siga abierta y volvé a probar. Esta falla ocurre antes de que el servidor reciba la solicitud, por lo que no queda registrada en el log del backend.');
    }
    let body;
    try { body=await response.json(); }
    catch { body=null; }
    if(!response.ok){
      let reason=`La solicitud falló (HTTP ${response.status}).`;
      if(typeof body?.detail==='string') reason=body.detail;
      else if(Array.isArray(body?.detail)){
        reason=body.detail.map(item=>{
          const field=Array.isArray(item.loc)?item.loc.filter(part=>part!=='body'&&part!=='query'&&part!=='path').join('.'):'';
          const message=typeof item.msg==='string'?item.msg:'Dato inválido';
          return field?`${field}: ${message}`:message;
        }).join(' · ')||reason;
      }
      const code=typeof body?.error_code==='string'?body.error_code:null;
      const requestId=typeof body?.request_id==='string'?body.request_id:response.headers.get('X-Request-ID');
      const extra=[code?`Código: ${code}`:null,requestId?`Referencia: ${requestId}`:null].filter(Boolean);
      if(extra.length) reason+=` [${extra.join(' · ')}]`;
      if(typeof body?.next_action==='string'&&body.next_action) reason+=` Acción sugerida: ${body.next_action}`;
      if(body?.should_log===true&&body?.registered_in_log===true) reason+=' Registro: la incidencia se guardó en netsentinel-errors.jsonl.';
      else if(body?.should_log===true&&body?.registered_in_log===false) reason+=' Registro: no se pudo escribir netsentinel-errors.jsonl; revisá permisos y espacio en disco.';
      else if(body?.should_log===false) reason+=' Registro: no se guarda como fallo interno porque es una validación o un rechazo previsto.';
      throw new Error(reason);
    }
    if(body===null) { const requestId=response.headers.get('X-Request-ID'); throw new Error('El servidor local devolvió una respuesta que no se pudo interpretar. Código NS-CONN-002.'+(requestId?' Referencia: '+requestId+'.':'')+' Recargá el panel; si persiste, compartí el registro de la solicitud.'); }
    return body;
  }
  async function refresh() {
    try {
      const [summary,devices,events,scans]=await Promise.all([api('/api/summary'),api('/api/devices?q='+encodeURIComponent($('searchInput').value)),api('/api/events?limit=30'),api('/api/scans?limit=12')]);
      state.devices=devices;state.events=events;state.scans=scans;
      $('totalMetric').textContent=summary.devices_total;$('trustedMetric').textContent=summary.devices_trusted;$('unknownMetric').textContent=summary.devices_untrusted;$('eventsMetric').textContent=summary.events_pending;
      $('lastScanMetric').textContent=summary.last_scan?`Última lectura: ${dateTime(summary.last_scan)}`:'Última lectura: todavía ninguna';
      $('gettingStarted').hidden=Number(summary.devices_total)>0;
      renderDevices();renderEvents();renderScans();
    } catch(error) { toast(`No se pudo actualizar: ${error.message}`); }
  }
  function renderDevices() {
    const tbody=$('devicesBody');$('deviceCount').textContent=`${state.devices.length} dispositivo${state.devices.length===1?'':'s'}`;
    if(!state.devices.length){
      const searching=$('searchInput').value.trim().length>0;
      const title=searching?'No encontramos coincidencias':'Todavía no hay dispositivos';
      const message=searching
        ?'Probá con otra IP, dirección MAC, fabricante o nombre.'
        :'Conectá tus equipos a la red y pulsá «Descubrir dispositivos». La búsqueda es local y algunos equipos no responden.';
      tbody.innerHTML='<tr><td colspan="6"><div class="empty"><strong>'+title+'</strong>'+message+'</div></td></tr>';
      return;
    }
    const localAddresses=latestLocalAddresses();
    tbody.innerHTML=state.devices.map(d=>`<tr><td><div class="device-name">${escapeHtml(d.display_name||d.ip_address||'Dispositivo')}</div><div class="device-meta">IP principal: ${escapeHtml(d.ip_address)} · visto ${escapeHtml(dateTime(d.first_seen))}</div>${localAddresses.has(d.ip_address)?'<div class="device-meta">IP local de esta computadora según la última lectura</div>':''}<details><summary>${(d.addresses||[]).length||1} dirección(es) observada(s)</summary><div>${(d.addresses||[]).map(a=>`<div class="device-meta">${escapeHtml(a.ip_address)} · última: ${escapeHtml(dateTime(a.last_seen))} · ${escapeHtml(a.source||'origen desconocido')}</div>`).join('')}</div></details></td><td><code>${escapeHtml(d.mac_address)}</code><div class="device-meta" title="${escapeHtml(d.manufacturer_source||'No se configuró una base OUI local')}${d.manufacturer_checked_at?' · consultada: '+escapeHtml(dateTime(d.manufacturer_checked_at)):''}">${escapeHtml(d.manufacturer||'Fabricante sin identificar')}${d.mac_locally_administered?' · MAC local (posiblemente aleatoria)':''}</div></td><td>${escapeHtml(d.interface||'—')}${['awdl0','llw0'].includes(String(d.interface||'').toLowerCase())?'<div class="device-meta">Interfaz Apple de enlace local (virtual)</div>':''}</td><td><span class="pill ${d.trusted?'good':'warn'}">${d.trusted?'✓ De confianza':'! Pendiente'}</span></td><td>${escapeHtml(dateTime(d.last_seen))}</td><td><div class="history-actions"><button class="tiny quiet" data-history="${d.id}">Historial</button><button class="tiny quiet" data-edit="${d.id}">Editar</button><button class="tiny quiet" data-ptr="${d.id}" title="Consultar DNS inverso bajo demanda">DNS PTR</button><button class="tiny ${d.trusted?'quiet':'primary'}" data-trust="${d.id}" data-next="${!d.trusted}">${d.trusted?'Revocar confianza':'Marcar conocido'}</button></div></td></tr>`).join('');
    tbody.querySelectorAll('[data-ptr]').forEach(button=>button.addEventListener('click',async()=>{
      const deviceId=button.dataset.ptr;button.disabled=true;const originalText=button.textContent;button.textContent='Consultando…';
      try{const result=await api('/api/devices/'+deviceId+'/dns-reverse');toast('DNS PTR · '+result.ip+' → '+result.hostname+' · '+(result.cache_hit?'resultado en caché':'consulta nueva')+' · nombre DNS no verificado');}
      catch(error){toast('DNS PTR: '+error.message);}
      finally{button.disabled=false;button.textContent=originalText;}
    }));
    tbody.querySelectorAll('[data-trust]').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true;try{await api(`/api/devices/${button.dataset.trust}`,{method:'PATCH',body:JSON.stringify({trusted:button.dataset.next==='true'})});toast(button.dataset.next==='true'?'Dispositivo marcado como de confianza.':'Confianza revocada.');await refresh();}catch(e){toast(e.message);button.disabled=false;}}));
    tbody.querySelectorAll('[data-history]').forEach(button=>button.addEventListener('click',async()=>{
      const id=button.dataset.history;button.disabled=true;$('historyContent').innerHTML='<div class="empty">Cargando historial…</div>';
      $('historyDialog').showModal();
      try{const data=await api('/api/devices/'+id+'/history?limit=200');
        $('historyTitle').textContent='Historial · '+(data.device.display_name||data.device.ip_address||('Dispositivo '+id));
        $('historySubtitle').textContent=data.count+' observación(es) recuperadas; más recientes primero.';
        $('historyContent').innerHTML=data.observations.length?data.observations.map(item=>'<div class="event"><div class="dot info"></div><div><div class="event-title">'+escapeHtml(item.ip_address)+'</div><div class="event-meta">'+escapeHtml(dateTime(item.observed_at))+' · Fuente: '+escapeHtml(item.source||item.scan_source||'desconocida')+'</div></div></div>').join(''):'<div class="empty">Todavía no hay observaciones guardadas para este dispositivo. Ejecutá un descubrimiento local para empezar a construir el historial.</div>';
      }catch(error){$('historyContent').textContent='No se pudo cargar el historial: '+error.message;}
      finally{button.disabled=false;}
    }));
    tbody.querySelectorAll('[data-edit]').forEach(button=>button.addEventListener('click',()=>{const device=state.devices.find(item=>item.id===Number(button.dataset.edit));if(!device)return;$('editDialog').dataset.deviceId=device.id;$('editName').value=device.display_name||'';$('editNotes').value=device.notes||'';$('editDialog').showModal();}));
  }
  function renderEvents() {
    const box=$('eventsList');
    const localAddresses=latestLocalAddresses();
    if(!state.events.length){box.innerHTML='<div class="empty"><strong>No hay eventos todavía</strong>Los dispositivos nuevos aparecerán después de la primera lectura.</div>';return;}
    box.innerHTML=state.events.map(e=>{
      const isLocalDevice=e.event_type==='new_device'&&localAddresses.has(e.ip_address);
      const eventDevice=state.devices.find(device=>device.mac_address===e.mac_address);
      const isAppleLinkInterface=['awdl0','llw0'].includes(String(eventDevice?.interface||'').toLowerCase());
      const title=isLocalDevice?'Equipo local identificado':isAppleLinkInterface&&e.event_type==='new_device'?'Interfaz Apple de enlace local':e.event_type==='new_device'?'Dispositivo nuevo':e.event_type==='trust_changed'?'Cambio de confianza':e.event_type==='ip_changed'?'Cambio de IPv4':e.event_type==='new_address'?'Nueva dirección':e.event_type;
      const message=isLocalDevice?'Esta IP coincide con la dirección local de la computadora que ejecuta NetSentinel.':isAppleLinkInterface?'La observación proviene de una interfaz Apple de enlace local y no identifica necesariamente un equipo de la LAN.':e.message;
      return `<div class="event"><div class="dot ${e.severity==='info'?'info':''}"></div><div><div class="event-title">${escapeHtml(title)}</div><div class="event-meta">${escapeHtml(dateTime(e.created_at))} · ${escapeHtml(e.mac_address||'Sin dispositivo asociado')} ${e.ip_address?'· '+escapeHtml(e.ip_address):''}</div><div class="event-message">${escapeHtml(message)}</div>${e.acknowledged?'':'<div class="event-actions"><button class="tiny quiet" data-ack="'+e.id+'">Marcar revisado</button></div>'}</div></div>`;
    }).join('');
    box.querySelectorAll('[data-ack]').forEach(button=>button.addEventListener('click',async()=>{try{await api(`/api/events/${button.dataset.ack}`,{method:'PATCH',body:JSON.stringify({acknowledged:true})});await refresh();}catch(e){toast(e.message);}}));
  }
  function renderScans() {
    const box=$('scansList');
    if(!state.scans.length){box.innerHTML='<div class="empty"><strong>Sin lecturas registradas</strong>Usá “Descubrir dispositivos” para buscar equipos en las subredes locales detectadas.</div>';return;}
    box.innerHTML=state.scans.map(scan=>{
      const report=scan.discovery||{};
      const networks=(report.networks||[]).map(n=>`${escapeHtml(n.network)} (${escapeHtml(n.interface)})${n.range_limited?' · rango limitado a /24':''}`).join(', ');
      const checked=Number.isFinite(Number(report.addresses_checked))?Number(report.addresses_checked):null;
      const responses=Number.isFinite(Number(report.ping_responses))?Number(report.ping_responses):null;
      const duration=Number.isFinite(Number(report.duration_seconds))?`Duración: ${Number(report.duration_seconds).toFixed(1)} s.`:'';
      const summary=checked!==null?`Direcciones consultadas: ${checked}; respuestas ping: ${responses??0}.`:'';
      return `<div class="event"><div class="dot ${scan.errors&&scan.errors.length?'':'info'}"></div><div><div class="event-title">Lectura #${scan.id} · ${Number(scan.devices_found)} dispositivo(s)</div><div class="event-meta">${escapeHtml(dateTime(scan.started_at))} · Fuente: ${escapeHtml(scan.source||'—')}</div>${networks?`<div class="event-message">Redes detectadas: ${networks}</div>`:''}${summary?`<div class="event-message">${escapeHtml(summary)}</div>`:''}${duration?`<div class="event-message">${escapeHtml(duration)}</div>`:''}<div class="event-message">${scan.errors&&scan.errors.length?escapeHtml(scan.errors.join(' · ')):'Sin errores informados por las fuentes disponibles.'}</div></div></div>`;
    }).join('');
  }
  $('gettingStartedScanBtn').addEventListener('click',()=>$('scanBtn').click());
  $('scanBtn').addEventListener('click',async()=>{if(!window.confirm('NetSentinel detectará automáticamente hasta dos subredes IPv4 privadas y consultará hasta 254 direcciones por subred con un solo ping por dirección. Esto genera tráfico en tu red local, sin modificar equipos ni explorar Internet. ¿Querés continuar?'))return;const button=$('scanBtn');button.disabled=true;button.textContent='Buscando…';try{const result=await api('/api/scan',{method:'POST'});const errors=(result.errors||[]).length?` Avisos: ${result.errors.join(' · ')}`:'';const scope=result.discovery?.networks||[];const networkText=scope.length?' Redes: '+scope.map(n=>n.network+' ('+n.interface+')').join(', ')+'. Direcciones consultadas: '+(result.discovery.addresses_checked||0)+'; respuestas ping: '+(result.discovery.ping_responses||0)+'.':'';toast(`${result.message} Equipos: ${result.devices_found}; direcciones: ${result.addresses_found}; nuevos: ${result.new_devices}.${networkText}${errors}`);await refresh();}catch(error){toast(`Falló el descubrimiento: ${error.message}`);}finally{button.disabled=false;button.textContent='⌕ Descubrir dispositivos';}});
  $('closeHistory').addEventListener('click',()=>$('historyDialog').close());
  $('cancelEdit').addEventListener('click',()=>$('editDialog').close());
  $('editForm').addEventListener('submit',async(event)=>{event.preventDefault();const dialog=$('editDialog');const id=dialog.dataset.deviceId;try{await api(`/api/devices/${id}`,{method:'PATCH',body:JSON.stringify({display_name:$('editName').value,notes:$('editNotes').value})});dialog.close();toast('Ficha del dispositivo actualizada.');await refresh();}catch(e){toast(e.message);}});
  $('refreshBtn').addEventListener('click',refresh);
  $('searchInput').addEventListener('input',()=>{window.clearTimeout(refresh.searchTimer);refresh.searchTimer=window.setTimeout(refresh,180);});
  $('diagBtn').addEventListener('click',async()=>{if(!window.confirm('El diagnóstico consultará DNS para example.com y enviará ping al router (si se detecta) y a 1.1.1.1. Estas pruebas generan tráfico de salida. ¿Querés continuar?'))return;const button=$('diagBtn');button.disabled=true;button.textContent='Comprobando…';$('diagnosticsBox').innerHTML='<div class="empty">Ejecutando comprobaciones…</div>';try{const result=await api('/api/diagnostics',{method:'POST'});const a=result.assessment;const summary='<div class="check diagnosis-summary"><div class="check-top"><strong>'+escapeHtml(a.title)+'</strong><span class="pill '+(a.status==='ok'?'good':'warn')+'">'+(a.status==='ok'?'Buen resultado':'Revisar')+'</span></div><div class="check-detail">'+escapeHtml(a.summary)+'</div>'+((a.next_steps||[]).length?'<ol class="diagnosis-steps">'+a.next_steps.map(step=>'<li>'+escapeHtml(step)+'</li>').join('')+'</ol>':'')+'</div>';$('diagnosticsBox').innerHTML=`<div class="diagnostics">${summary}${result.checks.map(c=>`<div class="check"><div class="check-top"><span>${escapeHtml(c.name)}</span><span class="pill ${c.status==='ok'?'good':c.status==='error'||c.status==='warning'||c.status==='timeout'?'warn':'info'}">${c.status==='ok'?'Correcto':c.status==='warning'?'Revisar':c.status==='timeout'?'Tiempo agotado':c.status==='error'?'Error de ejecución':'Omitido'}</span></div><div class="check-detail">${escapeHtml(c.detail)}</div>${c.error_code?'<div class="check-detail"><strong>'+escapeHtml(c.error_code)+'</strong> · '+(c.should_log?(c.logged?'Falla local registrada en netsentinel-errors.jsonl.':'No se pudo guardar el registro local; revisá permisos y espacio en disco.'):'No se registra como fallo interno: es un resultado de entorno/red o una prueba sin respuesta.')+'</div>':''}</div>`).join('')}<div class="check-detail">${escapeHtml(result.notice)}${result.request_id?' Referencia: '+escapeHtml(result.request_id)+'.':''}</div></div>`;}catch(e){$('diagnosticsBox').innerHTML=`<div class="empty">${escapeHtml(e.message)}</div>`;}finally{button.disabled=false;button.textContent='◉ Diagnóstico';}});
  api('/api/health').then(info=>{ $('appVersion').textContent='NetSentinel v'+info.version+' · Datos guardados en tu computadora'; }).catch(()=>{});
  refresh();
