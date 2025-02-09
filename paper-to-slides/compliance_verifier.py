from .error_handling import retry

class ComplianceVerifier:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    @retry(max_retries=3)
    def verify(self, slides):
        """Verify academic compliance requirements"""
        checks = [
            self._check_disclosures,
            self._validate_citations,
            self._verify_ethics
        ]
        
        for check in checks:
            if not check(slides):
                return False
        return True

    def _check_disclosures(self, slides):
        prompt = f"""Check for required disclosures in slides:
        {slides}
        
        Verify presence of:
        1. Funding sources
        2. Competing interests
        3. Data availability statement
        4. IRB/ethics approval"""
        return "All disclosures present" in self.llm.process(prompt)

    def _validate_citations(self, slides):
        prompt = f"""Verify citation integrity:
        {slides}
        
        Check:
        1. All claims are properly cited
        2. No missing references
        3. Consistent citation style"""
        return "Citation validation passed" in self.llm.process(prompt)

    def _verify_ethics(self, slides):
        prompt = f"""Check for ethical compliance:
        {slides}
        
        Verify:
        1. Human subject protections
        2. Animal research protocols
        3. Dual use potential disclosure"""
        return "Ethics check passed" in self.llm.process(prompt) 