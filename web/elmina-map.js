/* Shared by the phone picker and read-only management view. No location permissions. */
(async function(){
 const status=document.getElementById('status'),fixed=document.getElementById('fixed-pin'),params=new URLSearchParams(location.search);
 let config,ready=false,map;
 function notify(type,point){
  const value={type,map_id:config?.map_id,...point};
  if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify(value));
  if(window.parent!==window){try{const origin=new URL(params.get('parent_origin')||location.origin).origin;window.parent.postMessage(value,origin);}catch{}}
 }
 function fail(){status.hidden=false;status.textContent='Map unavailable. Check your connection and retry.';notify('bioguard:map-error');}
 try{
  const response=await fetch('/officer-assets/elmina-map-config.json');if(!response.ok)throw new Error('config');config=await response.json();
  if(!window.L)throw new Error('library');
  const allowed=L.latLngBounds(config.bounds),picker=params.get('mode')!=='view';
  const valid=(latitude,longitude)=>Number.isFinite(latitude)&&Number.isFinite(longitude)&&allowed.contains([latitude,longitude]);
  const initialLat=Number(params.get('latitude')),initialLng=Number(params.get('longitude'));
  const supplied=params.has('latitude')&&params.has('longitude')&&valid(initialLat,initialLng);
  const initial=supplied?[initialLat,initialLng]:config.center;
  if(!picker&&!supplied)throw new Error('point');
  map=L.map('map',{zoomControl:false,maxBounds:allowed.pad(1),maxBoundsViscosity:1,minZoom:config.min_zoom,maxZoom:config.max_zoom,scrollWheelZoom:true,touchZoom:true,inertia:false,bounceAtZoomLimits:false});
  const point=()=>{const p=map.getCenter();return{latitude:Math.max(allowed.getSouth(),Math.min(allowed.getNorth(),p.lat)),longitude:Math.max(allowed.getWest(),Math.min(allowed.getEast(),p.lng))};};
  function restrict(){const current=map.getCenter(),bounded=point();if(Math.abs(current.lat-bounded.latitude)>1e-9||Math.abs(current.lng-bounded.longitude)>1e-9){map.panTo([bounded.latitude,bounded.longitude],{animate:false});return true;}return false;}
  const tiles=L.tileLayer(config.tile_url,{maxZoom:config.max_zoom,maxNativeZoom:config.max_zoom,bounds:allowed,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>',crossOrigin:false});
  let loaded=0;
  tiles.on('tileload',()=>{loaded++;});
  tiles.on('load',()=>{if(loaded===0){fail();return;}ready=true;status.hidden=true;notify('bioguard:map-ready',point());});
  tiles.addTo(map);
  map.setView(initial,config.initial_zoom,{animate:false});restrict();
  // Mask outside the pilot area while allowing the centre pin to reach its boundary.
  const sw=config.bounds[0],ne=config.bounds[1];
  L.polygon([[[-85,-180],[-85,180],[85,180],[85,-180]],[[sw[0],sw[1]],[ne[0],sw[1]],[ne[0],ne[1]],[sw[0],ne[1]]]],{stroke:false,fillColor:'#eaf0e7',fillOpacity:1,interactive:false}).addTo(map);
  if(picker)fixed.hidden=false;
  else L.marker(initial,{icon:L.icon({iconUrl:'/officer-assets/location-pin.svg',iconSize:[36,48],iconAnchor:[18,47]}),keyboard:true,alt:'Reported plant location'}).addTo(map);
  map.on('moveend',()=>{if(restrict())return;if(ready&&picker)notify('bioguard:map-point',point());});
  map.on('resize',restrict);
  const observer=new ResizeObserver(()=>{map.invalidateSize({pan:false});restrict();});observer.observe(document.getElementById('map'));
  window.addEventListener('pagehide',()=>{observer.disconnect();map.remove();},{once:true});
  setTimeout(()=>{if(!ready)fail();},20000);
 }catch{fail();}
})();
