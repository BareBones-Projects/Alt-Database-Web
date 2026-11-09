// BareBones Projects, Designed by: Justin Levesque-Welsch.
export const CATEGORIES = Object.freeze({
  fandom: ['character','faction','species','organization','person','crew'],
  wiki: null,
  alt: ['location','star','planet','moon','system','hex','station','transit','sector','district']
});
export function normalizeEntries(payload) {
  const entries = Array.isArray(payload) ? payload : payload?.entries ?? payload?.items ?? payload?.results ?? [];
  if (!Array.isArray(entries)) throw new TypeError('Unexpected public API response');
  return entries.filter(item => item && typeof item === 'object' && item.visibility !== 'private' && item.visibility !== 'draft');
}
export function selectEntries(entries, view, query='') {
  const kinds=CATEGORIES[view], term=query.trim().toLocaleLowerCase();
  return entries.filter(item=>{
    const kind=String(item.kind ?? item.type ?? '').toLocaleLowerCase();
    if(kinds && !kinds.includes(kind)) return false;
    const haystack=[item.id,item.name,item.title,item.description,item.summary,kind].map(x=>String(x??'')).join(' ').toLocaleLowerCase();
    return !term || haystack.includes(term);
  });
}
export function makeApiUrl(base, path){
  const u=new URL(base);
  if(!['https:','http:'].includes(u.protocol)) throw new Error('API must use HTTP(S)');
  if(u.username||u.password||u.search||u.hash) throw new Error('API URL cannot include credentials or query');
  return new URL(path.replace(/^\//,''),u.href.replace(/\/*$/,'/') ).href;
}