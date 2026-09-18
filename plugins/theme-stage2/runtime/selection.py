"""Check an explicitly curated selection; do not invent or auto-detect assets."""
from pathlib import Path
from collections import Counter, defaultdict
import copy
import hashlib
import json

DEFAULT_POLICY = Path(__file__).resolve().parent/'profiles/representative-selection-v1.json'
ASSET_CATEGORIES = ('building','vehicle','facility','character')

def load_selection_policy(path=DEFAULT_POLICY):
    path=Path(path).resolve()
    p=json.loads(path.read_text())
    if p.get('schema')!='stage2.selection-policy.v1':
        raise ValueError('Unsupported selection policy')
    limits=p['asset_count']
    if not (0 < limits['minimum_target'] <= limits['recommended'] <= limits['maximum_target']):
        raise ValueError('Invalid selection count targets')
    if p['background']['counts_toward_asset_budget'] is not False:
        raise ValueError('Background must not consume the representative asset budget')
    source=(path.parent/p['source']['snapshot']).resolve()
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=p['source']['snapshot_sha256']:
        raise ValueError('Selection-policy source changed or is missing')
    return p

def resolve_selection_policy(inventory, policy=None):
    p = copy.deepcopy(policy if policy is not None else load_selection_policy())
    override = inventory.get('selection_override')
    if override is None:
        return p
    if not isinstance(override, dict) or not str(override.get('user_instruction', '')).strip():
        raise ValueError('selection_override requires user_instruction')
    unknown = set(override) - {'user_instruction', 'asset_count', 'allocation', 'background_count'}
    if unknown:
        raise ValueError('Unknown selection override fields: ' + ', '.join(sorted(unknown)))
    allocation = override.get('allocation')
    if allocation is not None:
        if not isinstance(allocation, dict) or not allocation or set(allocation) - set(ASSET_CATEGORIES):
            raise ValueError('Invalid selection override allocation')
        if any(type(v) is not int or v < 0 for v in allocation.values()):
            raise ValueError('Allocation counts must be nonnegative integers')
        p['recommended_allocation'] = {c: allocation.get(c, 0) for c in ASSET_CATEGORIES}
        p['allocation_is_flexible'] = False
    count = override.get('asset_count', sum(allocation.values()) if allocation is not None else None)
    if count is not None:
        if type(count) is not int or count <= 0:
            raise ValueError('Asset count must be a positive integer')
        if allocation is not None and sum(allocation.values()) != count:
            raise ValueError('Asset count and allocation disagree')
        for key in ('minimum_target', 'maximum_target', 'recommended'):
            p['asset_count'][key] = count
        if allocation is None:
            p['recommended_allocation'] = {}
            p['allocation_is_flexible'] = True
    if 'background_count' in override:
        count = override['background_count']
        if type(count) is not int or count < 0:
            raise ValueError('Background count must be a nonnegative integer')
        p['background']['recommended_count'] = count
    p['user_override'] = copy.deepcopy(override)
    return p

def assess_selection(inventory, policy=None):
    p=resolve_selection_policy(inventory, policy)
    rows=inventory.get('items',[])
    if not isinstance(rows,list):
        raise ValueError('Inventory items must be a list')
    groups=defaultdict(list)
    counts=Counter()
    blockers=[]
    backgrounds=[]
    missing_annotations=[]
    ids=[]
    for item in rows:
        iid=item.get('id');ids.append(iid)
        category=item.get('category')
        if category=='background':
            backgrounds.append(iid);continue
        if category not in ASSET_CATEGORIES:
            blockers.append('Unknown category for '+str(iid));continue
        key=item.get('prototype_key',iid)
        if not isinstance(key,str) or not key.strip():
            blockers.append('Missing prototype identity for '+str(iid));continue
        groups[key].append(iid)
        counts[category]+=1
        evidence=item.get('source_evidence',{})
        if evidence.get('present') is False:
            blockers.append('Selected object explicitly absent from source: '+str(iid))
        if item.get('source_bbox') is None and not evidence.get('basis'):
            missing_annotations.append(iid)
    if len(ids)!=len(set(ids)):
        blockers.append('Duplicate inventory IDs')
    duplicates={k:v for k,v in groups.items() if len(v)>1}
    if duplicates:
        blockers.append('Repeated prototypes must be merged before generating the representative set')
    count=len(groups)
    limits=p['asset_count']
    within=limits['minimum_target']<=count<=limits['maximum_target']
    state='needs_revision' if blockers else 'within_target' if within else 'under_target' if count<limits['minimum_target'] else 'over_target'
    notes=[]
    if not within:
        notes.append(f"Selected {count} distinct assets; target is {limits['minimum_target']}–{limits['maximum_target']}, default {limits['recommended']}.")
    if count<limits['minimum_target']:
        notes.append('Do not invent assets or add color-only variants to fill the shortfall; record source availability and adjust the plan.')
    if len(backgrounds)!=p['background']['recommended_count']:
        notes.append('The normal delivery has one separate background; the background does not count as an asset prototype.')
    for category,recommended in p['recommended_allocation'].items():
        if counts[category]!=recommended:
            notes.append(f'{category}: {counts[category]} selected, {recommended} required by the current selection policy.')
            if not p.get('allocation_is_flexible', True):
                state='needs_revision'
    if missing_annotations:
        notes.append('Source-evidence annotations still needed for: '+', '.join(str(x) for x in missing_annotations))
    return {'schema':'stage2.selection-assessment.v1','policy_id':p['id'],'policy_version':p['version'],
        'state':state,'selected_asset_entries':sum(counts.values()),'distinct_asset_prototypes':count,
        'background_count':len(backgrounds),'background_in_asset_count':False,
        'target':limits,'category_counts':{c:counts[c] for c in ASSET_CATEGORIES},
        'recommended_allocation':p['recommended_allocation'],'duplicate_prototypes':duplicates,
        'blocking_issues':blockers,'notes':notes,
        'scope':'Selection planning only; no automatic visual deduplication or image generation.'}
