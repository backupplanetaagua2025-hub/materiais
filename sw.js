/* Faz o site funcionar sem internet.
   - Guarda na instalação: a página, as miniaturas, as tabelas de preços e o manual.
   - O resto fica guardado depois da primeira vez que a pessoa abre ou baixa. */
self.window = self;
importScripts('_site/dados.js', '_site/refis.js');
var VERSAO = 'pa-materiais-' + (self.GERADO || '0') + '-r2';
var BASE = ['./', 'index.html', '_site/dados.js', '_site/produtos.js', '_site/refis.js', '_site/gota.png', '_site/icone-192.png', '_site/icone-512.png', '_site/manifest.webmanifest'];
function href(p){ return p.split('/').map(encodeURIComponent).join('/'); }
var ESSENCIAIS = (self.ARQUIVOS || []).reduce(function(l, it){
  if (it.mini) l.push(href(it.mini));
  var essencial = /^01 /.test(it.sec) || /Manual de Refis/i.test(it.nome);
  if (essencial) l.push(href(it.leve || it.arq));
  if (essencial && it.ext === 'pdf') l.push(href(it.arq));
  return l;
}, []);
(self.REFIS || []).forEach(function(r){ ESSENCIAIS.push(href(r.foto)); });
['industrial-25','industrial-50','industrial-100','uniq-25','uniq-50','uniq-100'].forEach(function(n){ ESSENCIAIS.push('_site/prod/' + n + '.jpg'); });

self.addEventListener('install', function(e){
  e.waitUntil(caches.open(VERSAO).then(function(c){
    return c.addAll(BASE).then(function(){
      return Promise.all(ESSENCIAIS.map(function(u){ return c.add(u).catch(function(){}); }));
    });
  }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(ks){
    return Promise.all(ks.filter(function(k){ return k.indexOf('pa-materiais-') === 0 && k !== VERSAO; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
function guardar(req, res){
  var n = +(res.headers.get('content-length') || 0);
  if (res.ok && res.type === 'basic' && n < 30 * 1048576) {
    var copia = res.clone(); caches.open(VERSAO).then(function(c){ c.put(req, copia); });
  }
  return res;
}
self.addEventListener('fetch', function(e){
  var r = e.request; if (r.method !== 'GET') return;
  var u = new URL(r.url); if (u.origin !== location.origin) return;
  var dinamico = r.mode === 'navigate' || /\/(index\.html)?$|_site\/(dados|produtos|refis)\.js$/.test(u.pathname);
  if (dinamico) {   // primeiro a internet (para pegar novidades), sem internet usa o guardado
    e.respondWith(fetch(r).then(function(res){ return guardar(r, res); }).catch(function(){
      return caches.match(r, {ignoreSearch: true}).then(function(m){ return m || caches.match('index.html'); });
    }));
    return;
  }
  e.respondWith(caches.match(r, {ignoreSearch: true}).then(function(m){
    return m || fetch(r).then(function(res){ return guardar(r, res); });
  }));
});
