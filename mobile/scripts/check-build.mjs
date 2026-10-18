import { pathToFileURL } from 'node:url';
export function validateBuildApi(value){
 let url;try{url=new URL(value);}catch{throw new Error('Set EXPO_PUBLIC_API_URL to your private beta HTTPS API.');}
 const host=url.hostname.toLowerCase();
 if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||host==='localhost'||host.endsWith('.localhost')||host==='[::1]'||host==='0.0.0.0'||host.startsWith('127.')||host.endsWith('.example')||host.endsWith('.invalid'))throw new Error('Use a real HTTPS API URL without credentials, query strings or a local placeholder.');
 return url.origin+url.pathname.replace(/\/+$/,'');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href&&process.env.EAS_BUILD)validateBuildApi(process.env.EXPO_PUBLIC_API_URL);
