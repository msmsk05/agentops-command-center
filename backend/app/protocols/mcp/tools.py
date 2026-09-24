DOCUMENTS = [
    {'title': 'Enterprise AI platform adoption report', 'company': 'Acme Research', 'text': 'Enterprise buyers prioritize governance, observability, and integration depth when selecting agent platforms.'},
    {'title': 'Agent platform benchmark', 'company': 'Northstar Labs', 'text': 'Multi-agent systems improve specialization but introduce coordination and evaluation overhead.'},
    {'title': 'Responsible AI controls', 'company': 'Policy Forum', 'text': 'Audit trails, human escalation, and evidence provenance are expected controls for production AI.'},
]

COMPANIES = {
    'acme': {'name': 'Acme Intelligence', 'sector': 'Enterprise software', 'employees': 4200, 'focus': 'Workflow automation'},
    'northstar': {'name': 'Northstar Labs', 'sector': 'AI infrastructure', 'employees': 860, 'focus': 'Developer tooling'},
}

MARKET_DATA = [
    {'company': 'Acme Intelligence', 'segment': 'Enterprise agents', 'growth_rate': 0.31, 'signal': 'governance demand'},
    {'company': 'Northstar Labs', 'segment': 'AI infrastructure', 'growth_rate': 0.27, 'signal': 'platform consolidation'},
]


def search_documents(query: str, limit: int = 5) -> list[dict]:
    terms = {term.lower() for term in query.split() if len(term) > 2}
    matches = [document for document in DOCUMENTS if terms.intersection(document['text'].lower().split()) or terms.intersection(document['title'].lower().split())]
    return matches[:limit]


def get_company_profile(company: str) -> dict:
    return COMPANIES.get(company.lower(), {'name': company, 'status': 'not_found'})


def retrieve_market_data(segment: str = 'enterprise agents') -> list[dict]:
    return [row for row in MARKET_DATA if segment.lower() in row['segment'].lower() or segment.lower() == 'all']
