import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>{
 const env=loadEnv(mode,process.cwd(),'');
 return {plugins:[react()],server:{host:'127.0.0.1',proxy:{'/api':{
  target:'http://127.0.0.1:8000',
  configure(proxy){proxy.on('proxyReq',(request)=>{
   // Secret remains in the local dev server; never bundled into React.
   if(env.API_KEY) request.setHeader('X-API-Key',env.API_KEY);
  })}
 }}}};
});
