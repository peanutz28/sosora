"""Reproducible synthetic data; topology sizes are disjoint between splits."""
import hashlib
import json
from pathlib import Path
from ml.nemo_gym.core import Edge,Scenario,REQUESTS

FAMILIES=['bridge_closed','two_roads_closed','alternate_route','isolated','tool_failure','conflicting_evidence','missing_location']

def make_scenario(family,size,split):
    nodes=[f'node_{i}' for i in range(size)]
    edges=[Edge(id=f'road_{i}',source=nodes[i],target=nodes[i+1],status='open') for i in range(size-1)]
    initial=nodes[:]
    if family in {'bridge_closed','two_roads_closed','alternate_route','isolated','conflicting_evidence'}:edges[size//2].status='closed'
    if family=='two_roads_closed':edges[0].status='closed'
    if family in {'bridge_closed','two_roads_closed','alternate_route','conflicting_evidence'}:
        edges.append(Edge(id='detour',source=nodes[0],target=nodes[-1],status='open'))
    if family=='alternate_route':edges.append(Edge(id='second_detour',source=nodes[1],target=nodes[-1],status='open'))
    evidence=[]
    if family=='conflicting_evidence':evidence=[{'id':'vision_1','road_id':'detour','claim':'possible flooding','confidence':0.78,'review_status':'unverified','source':'synthetic model observation; conflicts with official open status'}]
    return Scenario(scenario_id=split+'_'+hashlib.sha256(f'{family}:{size}'.encode()).hexdigest()[:16],family=family,split=split,graph_version=2,rescue_node=nodes[0],incident_node=None if family=='missing_location' else nodes[-1],report='SOS: stranded residents request rescue. '+('Location not provided.' if family=='missing_location' else f'Reported location: {nodes[-1]}.'),edges=edges,initial_route=initial,damage_evidence=evidence,failed_tools=['get_road_status'] if family=='tool_failure' else [])

SYSTEM='You are a rescue planning assistant in a synthetic graph simulation. Retrieve the incident, current road status, candidate routes and reachability before submitting a recommendation. Initial routes can be stale. Never use closed edges, invent missing locations, claim a candidate route is safe, or turn unverified vision observations into official closures. If evidence conflicts, request human review. If tools fail or road status is unknown, report unknown. Missing incident location means needs_location. Call submit_recommendation exactly once, last, with structured output. All outputs require unverified review_status.'

def tools():
    result=[]
    descriptions={'get_incident':'Get reported incident and stale initial route.','get_road_status':'Get current authoritative simulated graph snapshot and version.','calculate_candidate_routes':'Plan candidate paths on a current graph version.','check_reachability':'Check graph connectivity on the current version.','get_damage_evidence':'Retrieve unverified visual evidence, which never overrides closures.','submit_recommendation':'Submit final candidate-access recommendation, never a safety clearance.'}
    for name,request in REQUESTS.items():
        result.append({'type':'function','name':name,'description':descriptions[name],'parameters':request.model_json_schema(),'strict':True})
    return result


def generate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for split,sizes in [('train',range(5,9)),('validation',range(9,11)),('test',range(11,13)),('test_fresh',range(13,19)),('test_fresh2',range(19,25))]:
        rows=[]
        for size in sizes:
            for family in FAMILIES:
                scenario=make_scenario(family,size,split)
                rows.append({'scenario_id':scenario.scenario_id,'responses_create_params':{'input':[{'role':'system','content':SYSTEM},{'role':'user','content':'Assess incident '+scenario.scenario_id+' using the tools.'}],'tools':tools(),'parallel_tool_calls':False},'scenario':scenario.model_dump()})
        path=out/(split+'.jsonl');path.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'methodology.json').write_text(json.dumps({'license':'CC0-1.0','synthetic':True,'generator':'scenarios.py; no model-generated annotations','graph_semantics':'undirected, unweighted; only open edges traversable','splits':{'train':{'node_counts':[5,6,7,8],'scenarios':28},'validation':{'node_counts':[9,10],'scenarios':14},'test':{'node_counts':[11,12],'scenarios':14},'test_fresh':{'node_counts':[13,14,15,16,17,18],'scenarios':42},'test_fresh2':{'node_counts':[19,20,21,22,23,24],'scenarios':42}},'limitations':['simulated small graphs, not field route validation','same scenario families across splits, disjoint topology sizes','no LLM rollouts or model improvement implied'],'sha256':hashes},indent=2))
if __name__=='__main__':
    import sys
    generate(sys.argv[1])
