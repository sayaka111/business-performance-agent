from importlib import import_module
from ..models.schemas import BoundaryError, TransientError, ModuleResult

SKILLS = ('metric_compare','anomaly_evaluate','metric_decompose','contribution_analysis','dimension_drilldown','data_quality_guard','evidence_validate')

class Executor:
    def __init__(self, knowledge, query, state, trace, policy):
        self.knowledge, self.query, self.state, self.trace, self.policy = knowledge,query,state,trace,policy

    def call(self, name, **kwargs):
        if name not in SKILLS: raise ValueError('unregistered skill')
        function = import_module('business_performance_agent.skills.' + name).execute
        for attempt in range(self.policy['retry_limit'] + 1):
            try:
                result = function(self.knowledge,self.query,**kwargs)
            except TransientError as exc:
                result = ModuleResult('failed',reason='execution_failure',limitations=[str(exc)])
                retry = attempt < self.policy['retry_limit']
            except BoundaryError as exc:
                result = ModuleResult('blocked',reason=exc.reason,limitations=[exc.detail])
                retry = False
            except Exception as exc:
                result = ModuleResult('failed',reason='execution_failure',limitations=[f'{type(exc).__name__}: {exc}'])
                retry = False
            else:
                retry = result.status == 'failed' and attempt < self.policy['retry_limit']
            self.trace['skills_called'].append({'node':self.state.current_node,'skill':name,'attempt':attempt,'input':kwargs,'output':result.to_dict()})
            if retry:
                self.state.retry_count += 1
                continue
            self.state.warnings.extend(result.warnings)
            self.state.limitations.extend(result.limitations)
            return result
