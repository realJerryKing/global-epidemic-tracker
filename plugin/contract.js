// The only UI gateway endpoint; no method is a command or a conversation message.
export const pkg='@local/dsh-epidemic-tracker';
export const service='epidemicTracker';
export const descriptors=[{id:pkg+':'+service+'/panel',service,namespace:service,method:'panel',invocation:{kind:'direct'},parameters:[{name:'request',wire:'request',source:'json',codec:{mode:'src-json'}}],result:{mode:'src-json'}}];
