class ReportGenerator:
    def __init__(self,client=None): self.client=client

    def generate(self,result):
        """LLM may arrange validated phrases; free-form factual additions fail closed."""
        findings=result['key_findings']
        lines=[x['claim'] for x in findings]
        if self.client and findings:
            payload={'claims':[{'claim_id':x['claim_id'],'variants':[x['claim']]} for x in findings]}
            try:
                response=self.client.structured_generate(purpose='report',payload=payload,
                    schema={'type':'object','required':['selections'],'additionalProperties':False})
                selections=response['selections']
                by_id={x['claim_id']:x['claim'] for x in findings}
                if set(response)!={'selections'} or len(selections)!=len(by_id): raise ValueError('report additions/omissions')
                if {x['claim_id'] for x in selections}!=set(by_id): raise ValueError('report claims changed')
                if any(set(x)!={'claim_id','variant'} or x['variant']!=0 for x in selections): raise ValueError('unapproved wording')
                lines=[by_id[x['claim_id']] for x in selections]
            except Exception:
                lines=[x['claim'] for x in findings]
        return '\n'.join([f"GMV 诊断状态：{result['workflow_status']}",*lines,
            f"停止原因：{result['stop_reason']}",
            *['警告：'+x for x in result['warnings']],*['限制：'+x for x in result['limitations']],
            '以上为内部贡献定位，不证明外部因果；最终业务决策由人工完成。'])
