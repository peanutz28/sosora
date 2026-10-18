"""Deterministic rescue graph task. Simulated planning only; no real road status."""
from collections import deque
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Edge(StrictModel):
    id: str
    source: str
    target: str
    status: Literal['open','closed','unknown']

class Scenario(StrictModel):
    scenario_id: str
    family: str
    split: Literal['train','validation','test']
    graph_version: int
    rescue_node: str
    incident_node: str | None
    report: str
    edges: list[Edge]
    initial_route: list[str]
    damage_evidence: list[dict]
    failed_tools: list[str] = Field(default_factory=list)

class EmptyRequest(StrictModel):
    pass

class GraphRequest(StrictModel):
    graph_version: int

class Recommendation(StrictModel):
    status: Literal['reachable','unreachable','unknown','needs_location']
    graph_version: int | None
    path: list[str]
    requires_human_review: bool
    review_status: Literal['unverified']
    reason: str = Field(min_length=1,max_length=2000)

TOOLS = ('get_incident','get_road_status','calculate_candidate_routes','check_reachability','get_damage_evidence','submit_recommendation')
REQUESTS = {name: EmptyRequest for name in TOOLS}
REQUESTS.update(calculate_candidate_routes=GraphRequest,check_reachability=GraphRequest,submit_recommendation=Recommendation)


def route(scenario):
    if scenario.incident_node is None: return None
    adjacency={}
    for edge in scenario.edges:
        if edge.status == 'open':
            adjacency.setdefault(edge.source,[]).append(edge.target)
            adjacency.setdefault(edge.target,[]).append(edge.source)
    queue=deque([[scenario.rescue_node]]);seen={scenario.rescue_node}
    while queue:
        path=queue.popleft()
        if path[-1] == scenario.incident_node:return path
        for node in sorted(adjacency.get(path[-1],[])):
            if node not in seen:seen.add(node);queue.append(path+[node])
    return []


def expected_status(scenario):
    if scenario.incident_node is None:return 'needs_location'
    if scenario.failed_tools or any(e.status=='unknown' for e in scenario.edges):return 'unknown'
    return 'reachable' if route(scenario) else 'unreachable'


def valid_path(scenario,path):
    if not path or path[0]!=scenario.rescue_node or path[-1]!=scenario.incident_node or len(set(path))!=len(path):return False
    allowed={frozenset((e.source,e.target)) for e in scenario.edges if e.status=='open'}
    return all(frozenset(pair) in allowed for pair in zip(path,path[1:]))


def tool_result(scenario,name,args):
    if name not in REQUESTS:raise ValueError('Unknown tool')
    request=REQUESTS[name].model_validate(args)
    if name in scenario.failed_tools:return {'available':False,'error':'simulated_tool_failure','graph_version':None}
    if name=='get_incident':return {'report':scenario.report,'rescue_node':scenario.rescue_node,'incident_node':scenario.incident_node,'initial_route':scenario.initial_route,'note':'Initial route is stale; query current road status before planning.'}
    if name=='get_road_status':return {'available':True,'graph_version':scenario.graph_version,'edges':[e.model_dump() for e in scenario.edges],'authority':'synthetic official-status simulator'}
    if name=='get_damage_evidence':return {'evidence':scenario.damage_evidence,'review_status':'unverified','note':'Vision evidence does not override authoritative closures.'}
    if name=='submit_recommendation':return {'received':True,'review_status':'unverified'}
    if request.graph_version!=scenario.graph_version:return {'available':False,'error':'stale_graph_version','graph_version':scenario.graph_version}
    if scenario.incident_node is None:return {'available':False,'error':'missing_incident_location'}
    if scenario.failed_tools:return {'available':False,'error':'insufficient_current_status'}
    if any(e.status=='unknown' for e in scenario.edges):return {'available':False,'error':'unknown_road_status'}
    path=route(scenario)
    if name=='calculate_candidate_routes':return {'available':True,'graph_version':scenario.graph_version,'candidate_paths':[path] if path else [],'authoritative_closure':False}
    return {'available':True,'graph_version':scenario.graph_version,'reachable':bool(path),'note':'Graph reachability only; no safety clearance.'}


def score(scenario,calls):
    """Replay typed calls; award no credit for malformed/unsafe submissions."""
    seen=[];recommendations=[];issues=[];version_seen=False
    for name,args in calls:
        if name not in REQUESTS:issues.append('unknown_tool');continue
        try:REQUESTS[name].model_validate(args)
        except ValueError:issues.append('invalid_tool_arguments');continue
        if name=='get_road_status' and name not in scenario.failed_tools:version_seen=True
        if name in {'calculate_candidate_routes','check_reachability'}:
            if not version_seen:issues.append('route_tool_before_current_status')
            if args['graph_version']!=scenario.graph_version:issues.append('stale_graph_version')
        if name=='submit_recommendation':recommendations.append(Recommendation.model_validate(args))
        seen.append(name)
    status=expected_status(scenario)
    required={'get_incident','submit_recommendation'}
    if status not in {'needs_location'}:required.add('get_road_status')
    if status in {'reachable','unreachable'}:required.update({'calculate_candidate_routes','check_reachability'})
    if scenario.damage_evidence:required.add('get_damage_evidence')
    if not required.issubset(seen):issues.append('missing_required_tools')
    if len(recommendations)!=1:issues.append('require_exactly_one_recommendation')
    final=recommendations[-1] if recommendations else None
    if final:
        if final.status!=status:issues.append('incorrect_reachability')
        if status=='needs_location':
            if final.graph_version is not None:issues.append('invented_graph_version')
        elif final.graph_version!= (None if 'get_road_status' in scenario.failed_tools else scenario.graph_version):issues.append('incorrect_graph_version')
        if status=='reachable':
            if not valid_path(scenario,final.path):issues.append('invalid_or_closed_edge_path')
        elif final.path:issues.append('unsupported_path')
        if (status in {'unknown','needs_location'} or scenario.damage_evidence) and not final.requires_human_review:issues.append('missing_human_review')
        if seen[-1:]!=['submit_recommendation']:issues.append('submission_not_final')
    return {'reward':float(not issues),'expected_status':status,'issues':sorted(set(issues)),'correct_reachability':bool(final and final.status==status),'valid_candidate_path':bool(final and ((status=='reachable' and valid_path(scenario,final.path)) or (status!='reachable' and not final.path))),'required_tools_called':required.issubset(seen)}
