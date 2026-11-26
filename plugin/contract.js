// The only UI gateway endpoint; no method is a command or a conversation message.
export const pkg='@local/dsh-epidemic-tracker';
export const service='epidemicTracker';
export function panelDescriptors(z) {
  const create = () => z.strictObject({
    action: z.enum(['official','setup','regions','snapshot','enroll','read','save','withdraw']),
    region_code: z.string().regex(/^\d{6}$/).optional(),
    refresh: z.boolean().optional(),
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
    invite_code: z.string().optional(), symptom: z.enum(['new','ongoing','none']).optional(),
    observation: z.enum(['more','usual','less']).nullable().optional(),
    consent: z.boolean().optional(), confirm: z.boolean().optional()
  });
  const codec = { mode: 'strict', typeSymbol: pkg+'#epidemicTracker/panel:request', create };
  return [{ id:pkg+'#'+service+'/panel', service, namespace:service, method:'panel',
    invocation:{kind:'direct'}, parameters:[{name:'request',wire:'request',source:'json',codec}],
    result:{mode:'src-json'} }];
}
