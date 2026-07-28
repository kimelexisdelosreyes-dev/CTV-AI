import type { AIModelAdapter, AIModelAdapterRegistrySnapshot } from "@/contracts/model-runtime";
import type { AIExecutionMode, AIModelLocation, AIModelProviderType } from "@/contracts/orchestrator";
const freeze=<T>(v:T):T=>{if(v&&typeof v==="object"&&!Object.isFrozen(v)){Object.freeze(v);Object.values(v as Record<string,unknown>).forEach(freeze);}return v;};
export class AIModelAdapterRegistry {
  private readonly adapters = new Map<string, AIModelAdapter>();
  constructor(private readonly registryId="model-adapters", private readonly version="1") {}
  register(adapter: AIModelAdapter): void { const d=adapter.descriptor; if(!d.adapterId||this.adapters.has(d.adapterId)) throw new Error("Duplicate or missing adapter ID"); if(!Number.isFinite(d.priority)) throw new Error("Invalid adapter priority"); this.adapters.set(d.adapterId,adapter); }
  snapshot(): AIModelAdapterRegistrySnapshot { const adapters=[...this.adapters.values()].map(a=>a.descriptor).sort((a,b)=>a.adapterId.localeCompare(b.adapterId)); const sourceFingerprint=`adapter-registry-1:${this.registryId}:${this.version}:${adapters.map(a=>`${a.adapterId}:${a.adapterVersion}`).join(",")}`; return freeze({registryId:this.registryId,version:this.version,adapters,sourceFingerprint}); }
  resolve(input: Readonly<{modelId:string;providerType:AIModelProviderType;location:AIModelLocation;mode:AIExecutionMode}>): AIModelAdapter | undefined { return [...this.adapters.values()].filter(a=>a.descriptor.enabled&&a.descriptor.providerType===input.providerType&&a.descriptor.supportedModelIds.includes(input.modelId)&&a.descriptor.supportedLocations.includes(input.location)&&a.descriptor.supportedExecutionModes.includes(input.mode)&&a.supports(input)).sort((a,b)=>b.descriptor.priority-a.descriptor.priority||a.descriptor.adapterId.localeCompare(b.descriptor.adapterId))[0]; }
}
