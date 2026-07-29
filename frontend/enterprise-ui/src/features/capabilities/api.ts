export type CapabilitySummary={capability_id:string;name:string;description:string;category:string;version:string};
export type CapabilityExecutionResponse={request_id:string;capability_id:string;status:string;output:Record<string,string>;warnings:string[];trace_id:string};
const base=process.env.NEXT_PUBLIC_API_URL??"http://127.0.0.1:8000";
export async function listCapabilities(signal?:AbortSignal){const r=await fetch(`${base}/api/v1/capabilities`,{credentials:"include",signal});if(!r.ok)throw new Error("CAPABILITY_API_UNAVAILABLE");return r.json() as Promise<CapabilitySummary[]>}
export async function executeCapability(capability_id:string,input:string){const r=await fetch(`${base}/api/v1/capabilities/execute`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({capability_id,input:{text:input}})});if(!r.ok)throw new Error("CAPABILITY_EXECUTION_FAILED");return r.json() as Promise<CapabilityExecutionResponse>}
