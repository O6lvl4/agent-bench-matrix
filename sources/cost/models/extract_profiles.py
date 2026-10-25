"""Mechanically regenerate model-cost-models.json from preserved public API/config snapshots."""
import json,pathlib,datetime
P=pathlib.Path(__file__).parent
OUT=P.parent/'model-research.json'
MODELS=[
 ('qwen3-8b','Qwen/Qwen3-8B','Qwen/Qwen3-8B-GGUF'),
 ('qwen3-32b','Qwen/Qwen3-32B','Qwen/Qwen3-32B-GGUF'),
 ('qwen3-coder-30b-a3b','Qwen/Qwen3-Coder-30B-A3B-Instruct','ggml-org/Qwen3-Coder-30B-A3B-Instruct-GGUF'),
 ('gpt-oss-20b','openai/gpt-oss-20b','ggml-org/gpt-oss-20b-GGUF'),
 ('gpt-oss-120b','openai/gpt-oss-120b','ggml-org/gpt-oss-120b-GGUF'),
]
def load(n):return json.loads((P/n).read_text())
def key(s):return s.replace('/','__')
def meta(n):return load(n+'.meta.json')
def source(label,n):
 m=meta(n)
 return {'label':label,'url':m['source_url'],'retrieved_at_utc':m['retrieved_at_utc'],'snapshot_file':n,'snapshot_sha256':m['sha256']}
rtsha=load('llamacpp-commit.json')['sha']
profiles=[]
for mid,src,repo in MODELS:
 sk,rk=key(src),key(repo)
 sm,rm,cfg=load(sk+'.api.json'),load(rk+'.api.json'),load(sk+'.config.json')
 chosen=[x for x in load(rk+'.tree.json') if x['path'].endswith('.gguf') and ('Q4_K_M' in x['path'] or 'MXFP4' in x['path'])]
 assert len(chosen)==1
 f=chosen[0];head=load(rk+'.artifact-head.json');assert head['matches_linked_size']
 assert f['size']==f['lfs']['size']==int(head['headers']['x-linked-size'])
 oss=mid.startswith('gpt-oss');coder='coder' in mid
 mode='full-context-upper-bound' if oss else 'full-context'
 c={'layers':cfg['num_hidden_layers'],'kv_heads':cfg['num_key_value_heads'],'head_dim':cfg['head_dim'],
    'attention_heads':cfg['num_attention_heads'],'architecture':cfg['model_type'],
    'max_position_embeddings_config':cfg['max_position_embeddings'],'sliding_window':cfg.get('sliding_window'),
    'kv_mode':mode,'context_tokens':4096,'concurrent_sequences':1,'kv_dtype':'f16','bytes_per_element':2,
    'source_url':'https://huggingface.co/'+src+'/resolve/'+sm['sha']+'/config.json'}
 kv=2*c['layers']*c['kv_heads']*c['head_dim']*c['context_tokens']*c['concurrent_sequences']*c['bytes_per_element']
 if 'layer_types' in cfg:c['layer_types']=cfg['layer_types'];c['full_attention_layers']=cfg['layer_types'].count('full_attention');c['sliding_attention_layers']=cfg['layer_types'].count('sliding_attention')
 if coder or oss:c['experts']=cfg.get('num_experts',cfg.get('num_local_experts'));c['active_experts_per_token']=cfg['num_experts_per_tok']
 note='公開GGUFの正確なダウンロード容量と、設定ファイルから計算したKVキャッシュのデータ量です。実測VRAM/RAM使用量や動作保証ではありません。'
 constraints=['Use a current llama.cpp build with support for the selected architecture and quantization. Runtime support was documented, not benchmarked or execution-tested in this research.',
 'GGUF file bytes are storage bytes, not measured resident VRAM/RAM. Graph buffers, padding, backend allocations, driver/OS memory, memory mapping and offload policy can change actual requirements.',
 '4096 tokens means total cached context (prompt plus generated tokens), one concurrent sequence, f16 keys and values. This does not specify throughput-oriented prompt token batching.']
 if coder:
  note+=' MoEの「3B active」は保存する重みの容量ではありません。ggml-org版Q4_K_Mはexpertを量子化し、attention・embedding等をQ8_0で保持します。'
  constraints.append('The selected ggml-org Q4_K_M conversion uses base quantization for routed experts; embeddings and attention are kept at Q8_0. Active-parameter count must not be used for storage or residency sizing.')
 elif oss:
  note+=' MXFP4は通常の一律4-bit換算ではありません。全層に4096 tokenを割り当てるKV上限を表示していますが、実際は128-token sliding attentionとfull attentionが交互にあり、実行時の確保量は異なります。このMVPでは自動ハードウェア適合・最安判定の対象外です。'
  constraints += ['Native MXFP4 runtime support is documented for CPU, CUDA, Metal and Vulkan by llama.cpp maintainers. This does not establish the loaded allocation on any particular hardware.',
  'The source model requires the Harmony response format. Use a compatible embedded chat template/runtime.',
  'Alternating sliding-window (128 tokens) and full-attention layers are present. The displayed KV number is an unpadded full-context payload ceiling, not an upper bound on total runtime memory.',
  'MoE active parameters do not reduce total stored weights. No external EAGLE3/speculative model is included in the selected artifact.']
 else:
  note+=' Q4_K_Mは混合量子化のため、パラメータ数×0.5 byteではなく公開ファイル容量を使用します。4K contextは費用比較用の限定条件で、長い推論タスクの品質評価ではありません。'
  constraints.append('The official model card provides llama.cpp GGUF usage. The 4096-token cost scenario is deliberately shorter than the model card\'s recommended output budgets for complex reasoning; no quality equivalence is claimed.')
 profile={'model_id':mid,'model_name':src.split('/')[-1],
 'source_model':{'repository':src,'url':'https://huggingface.co/'+src,'revision':sm['sha']},
 'artifact':{'bytes':f['size'],'gib':f['size']/2**30,'gb_decimal':f['size']/10**9,
 'quantization':'MXFP4' if oss else 'Q4_K_M','format':'GGUF','repository':repo,'filename':f['path'],'revision':rm['sha'],
 'publisher_role':'model-publisher' if repo.startswith('Qwen/') else 'runtime-maintainer-conversion',
 'url':'https://huggingface.co/'+repo+'/blob/'+rm['sha']+'/'+f['path'],
 'download_url':head['url'],'lfs_sha256':f['lfs']['oid'],
 'byte_verification':'Hugging Face pinned tree API file.size = lfs.size = download HEAD x-linked-size',
 'download_head_status':head['status'],'retrieved_at_utc':head['retrieved_at_utc']},
 'runtime':'llama.cpp / GGUF (documented support; not execution-tested)',
 'runtime_details':{'name':'llama.cpp','source_url':'https://github.com/ggml-org/llama.cpp','inspected_revision':rtsha,'execution_tested':False,'benchmark_available':False},
 'license':{'name':'Apache-2.0','url':'https://huggingface.co/'+src+'/blob/'+sm['sha']+'/LICENSE'},
 'config':c,
 'kv_memory':{'bytes':kv,'gib':kv/2**30,'kind':'calculated-unpadded-payload','mode':mode,
 'formula':'2 (K and V) * layers * kv_heads * head_dim * context_tokens * concurrent_sequences * 2 (f16 bytes)',
 'not_included':['tensor padding/alignment','runtime graph and compute buffers','weights','runtime/driver memory','operating system memory'],
 'measured':False},
 'modeled_fit_eligible':not oss,'modeled_fit_status':'eligible-for-explicitly-assumed-capacity-estimate' if not oss else 'research-only-in-mvp',
 'modeled_fit_exclusion_reason':None if not oss else 'Native MXFP4 is supported, but no matched hardware/runtime resident-allocation validation was performed; alternating sliding/full-attention KV allocation needs runtime-specific validation.',
 'runtime_constraints':constraints,'notes_ja':note,
 'sources':[source('Source configuration',sk+'.config.json'),source('Source model card',sk+'.README.md'),source('Source license',sk+'.LICENSE'),source('Selected quantization model card',rk+'.README.md'),source('Pinned artifact byte metadata',rk+'.tree.json'),source('llama.cpp KV allocation implementation','llamacpp__src__llama-kv-cache.cpp')]}
 if oss:profile['sources'].append(source('Maintainer native MXFP4 support announcement','llamacpp-gpt-oss-announcement.txt') if (P/'llamacpp-gpt-oss-announcement.txt.meta.json').exists() else {'label':'Maintainer native MXFP4 support announcement','url':'https://github.com/ggml-org/llama.cpp/discussions/15095','retrieved_at_utc':load('llamacpp-gpt-oss-announcement.meta.json')['retrieved_at_utc'],'snapshot_file':'llamacpp-gpt-oss-announcement.txt','snapshot_sha256':load('llamacpp-gpt-oss-announcement.meta.json')['sha256']})
 if repo.startswith('ggml-org'):
  srcmap=(P/(rk+'..src_sha')).read_text()
  assert 'PRIMARY='+sm['sha'] in srcmap
  profile['artifact']['conversion_source_revision_verified']=True
 profiles.append(profile)
data={'schema_version':1,'retrieved_at_utc':max(json.loads(f.read_text())['retrieved_at_utc'] for f in P.glob('*.meta.json')), 
 'scope':'Five representative open-weight models; three Qwen capacity-estimate profiles plus two gpt-oss evidence-only profiles.',
 'methodology':{'storage_evidence':'Actual selected downloadable GGUF artifact bytes; no parameter-count times bits approximation.',
 'memory_evidence':'Source config dimensions derive unpadded f16 KV payload at 4096 cached tokens and one concurrent sequence. File size is not measured runtime memory.',
 'performance':'No tokens/s, latency, quality, minimum-memory or validated fit claim is made.',
 'runtime_overhead':'No overhead number is claimed from these sources. Any added 2 GiB buffer or 10/25 percent margin must be labeled an explicit planning assumption, not a measured requirement.',
 'provenance':'Public source snapshots and extraction script in model-cost-provenance. Artifact metadata is commit-pinned and independently checked against x-linked-size. Artifacts themselves were not downloaded.'},
 'profiles':profiles}
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(OUT)
for x in profiles:print(x['model_id'],x['artifact']['bytes'],x['kv_memory']['bytes'],x['modeled_fit_eligible'])
