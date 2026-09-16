"""Record real tool calls and prepare alpha; never invoke an image-generation API."""
from pathlib import Path
import hashlib
import json
import shutil
import uuid
from PIL import Image
import harness as h

def record_call(run, item_id, image, prompt, inputs, tool='image_gen.imagegen'):
    run, image, prompt = Path(run).resolve(), Path(image).resolve(), Path(prompt).resolve()
    m = h.read_json(run/'manifest.json')
    if 'scene_plan_contract' in m:
        pin = m['scene_plan_contract']
        if not pin.get('sha256') or h.file_hash(run/'scene-plan.json') != pin['sha256']:
            raise ValueError('Bind a valid scene plan before recording generation')
    item = next((i for i in m['items'] if i['id'] == item_id), None)
    if item is None or not inputs:
        raise ValueError('A known item and at least one traceable image input are required')
    allowed = {}
    for ref in item['generation_inputs']:
        allowed[h.inside(run,ref['file'])] = ref['sha256']
    previous = [h.read_json(h.inside(run,p)) for p in item.get('generation_records',[])]
    for call in previous:
        allowed[h.inside(run,call['raw_file'])] = call['raw_sha256']
    for file in item.get('processing_records',[]):
        processed = h.read_json(h.inside(run,file))
        if processed.get('raw_sha256') in allowed.values():
            allowed[h.inside(run,processed['output_file'])] = processed['output_sha256']
    actual_inputs = []
    for value in inputs:
        path = Path(value).resolve()
        digest = h.file_hash(path) if path.is_file() else None
        canonical = next((p for p,sha in allowed.items()
                          if digest==sha and p.is_file() and h.file_hash(p)==sha),None)
        if canonical is None:
            raise ValueError('Image input is not the current source, its crop, or a recorded output for this same item: '+str(path))
        actual_inputs.append({'file':canonical.relative_to(run).as_posix(),
                              'actual_input_path':str(value),'resolved_input_path':str(path),
                              'sha256':digest})
    with Image.open(image) as im:
        im.load()
        info = {'format':im.format, 'mode':im.mode, 'dimensions':list(im.size)}
    raw_hash, prompt_hash = h.file_hash(image), h.file_hash(prompt)
    identity = hashlib.sha256(json.dumps({'raw_source':str(image),'raw_sha256':raw_hash,
        'prompt_sha256':prompt_hash,'inputs':actual_inputs,'tool':tool},sort_keys=True).encode()).hexdigest()
    duplicate = next((p for p in previous if p.get('record_key')==identity),None)
    if duplicate:
        return {**duplicate,'idempotent':True}
    attempt = len(previous)+1
    directory = run/'calls'/item_id/(f'{attempt:02d}-'+uuid.uuid4().hex[:8])
    directory.mkdir(parents=True)
    raw_file = directory/('raw'+image.suffix.lower())
    prompt_file = directory/'actual.prompt.txt'
    shutil.copy2(image,raw_file);shutil.copy2(prompt,prompt_file)
    if h.file_hash(raw_file)!=raw_hash or h.file_hash(prompt_file)!=prompt_hash:
        raise ValueError('Tool output or prompt changed while recording')
    record = {'schema':'stage2.generation-call.v1','record_key':identity,'item_id':item_id,
        'attempt':attempt,'tool':tool,'completed_at':h.now(),
        'source_scene_sha256':m['source']['sha256'],'inputs':actual_inputs,
        'raw_source':str(image),'raw_file':raw_file.relative_to(run).as_posix(),'raw_sha256':raw_hash,
        'actual_prompt_file':prompt_file.relative_to(run).as_posix(),'actual_prompt_sha256':prompt_hash,
        'planned_prompt_file':item['prompt_file'],'planned_prompt_sha256':item['prompt_sha256'],
        'status':'recorded_pending_processing_and_visual_review',**info}
    record_file = directory/'call.json';h.write_json(record_file,record)
    item.setdefault('generation_records',[]).append(record_file.relative_to(run).as_posix())
    item['prompt_status'] = 'executed_exact_plan' if prompt_hash==item['prompt_sha256'] else 'executed_with_recorded_specialization'
    m['actual_generation_calls'] = sum(len(i.get('generation_records',[])) for i in m['items'])
    h.write_json(run/'manifest.json',m)
    return record

def cutout_candidate(run, item_id, image, matte='auto', shadowed_matte=False):
    from cutout import remove_matte, VERSION
    run, image = Path(run).resolve(), Path(image).resolve()
    m = h.read_json(run/'manifest.json')
    item = next((i for i in m['items'] if i['id']==item_id),None)
    if item is None or item['category']=='background':
        raise ValueError('Cutout applies to an independent asset, not the background')
    signature = {'raw_sha256':h.file_hash(image),'matte':matte,'shadowed_matte':shadowed_matte,'algorithm_version':VERSION}
    key = hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    folder = run/'processed'/item_id/key[:20]
    folder.mkdir(parents=True,exist_ok=True)
    output = folder/(item_id+'.png');record_file=folder/'processing.json'
    if output.exists():
        if not record_file.is_file() or h.read_json(record_file)['output_sha256']!=h.file_hash(output):
            raise ValueError('Existing processed output is untracked or changed')
        stats = h.read_json(record_file)
    else:
        im = Image.open(image)
        if im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255) and im.format=='PNG':
            shutil.copy2(image,output)
            stats={'method':'native alpha preserved byte-for-byte','interior_recoloring':False}
        else:
            out,stats = remove_matte(im,matte=matte,shadowed_matte=shadowed_matte)
            out.save(output)
        stats.update(signature,source_file=str(image),output_file=output.relative_to(run).as_posix(),
                     output_sha256=h.file_hash(output),created_at=h.now())
        h.write_json(record_file,stats)
    artifact = h.register(run,item_id,output,origin='local alpha preparation; not art-style approval')
    m = h.read_json(run/'manifest.json')
    item = next(i for i in m['items'] if i['id']==item_id)
    file = record_file.relative_to(run).as_posix()
    if file not in item.setdefault('processing_records',[]):
        item['processing_records'].append(file)
    h.write_json(run/'manifest.json',m)
    return {'artifact':artifact,'processing_record':file,'visual_review_required':True}
