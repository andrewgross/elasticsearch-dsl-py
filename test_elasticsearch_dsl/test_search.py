from elasticsearch_dsl import search, query, F, Q

def test_search_starts_with_empty_query():
    s = search.Search()

    assert s.query._proxied == query.MatchAll()

def test_search_query_combines_query():
    s = search.Search()

    s2 = s.query('match', f=42)
    assert s2.query._proxied == query.Match(f=42)
    assert s.query._proxied == query.MatchAll()

    s3 = s2.query('match', f=43)
    assert s2.query._proxied == query.Match(f=42)
    assert s3.query._proxied == query.Bool(must=[query.Match(f=42), query.Match(f=43)])

def test_methods_are_proxied_to_the_query():
    s = search.Search()

    assert s.query.to_dict() == {'match_all': {}}

def test_query_always_returns_search():
    s = search.Search()

    assert isinstance(s.query('match', f=42), search.Search)

def test_aggs_get_copied_on_change():
    s = search.Search()
    s.aggs.bucket('per_tag', 'terms', field='f').aggregate('max_score', 'max', field='score')

    s2 = s.query('match_all')
    s2.aggs.bucket('per_month', 'date_histogram', field='date', interval='month')
    s3 = s2.query('match_all')
    s3.aggs['per_month'].aggregate('max_score', 'max', field='score')
    s4 = s3._clone()
    s4.aggs.aggregate('max_score', 'max', field='score')

    d = {
        'query': {'match_all': {}},
        'aggs': {
            'per_tag': {
                'terms': {'field': 'f'},
                'aggs': {'max_score': {'max': {'field': 'score'}}}
             }
        }
    }

    assert d == s.to_dict()
    d['aggs']['per_month'] = {"date_histogram": {'field': 'date', 'interval': 'month'}}
    assert d == s2.to_dict()
    d['aggs']['per_month']['aggs'] = {"max_score": {"max": {"field": 'score'}}}
    assert d == s3.to_dict()
    d['aggs']['max_score'] = {"max": {"field": 'score'}}
    assert d == s4.to_dict()

def test_search_index():
    s = search.Search(index='i')
    assert s._index == ['i']
    s.index('i2')
    assert s._index == ['i', 'i2']
    s.index()
    assert s._index is None
    s = search.Search(index=('i', 'i2'))
    assert s._index == ['i', 'i2']
    s = search.Search(index=['i', 'i2'])
    assert s._index == ['i', 'i2']
    s = search.Search()
    s.index('i', 'i2')
    assert s._index == ['i', 'i2']

def test_search_doc_type():
    s = search.Search(doc_type='i')
    assert s._doc_type == ['i']
    s.doc_type('i2')
    assert s._doc_type == ['i', 'i2']
    s.doc_type()
    assert s._doc_type is None
    s = search.Search(doc_type=('i', 'i2'))
    assert s._doc_type == ['i', 'i2']
    s = search.Search(doc_type=['i', 'i2'])
    assert s._doc_type == ['i', 'i2']
    s = search.Search()
    s.doc_type('i', 'i2')
    assert s._doc_type == ['i', 'i2']

def test_search_to_dict():
    s = search.Search()
    assert {"query": {"match_all": {}}} == s.to_dict()

    s = s.query('match', f=42)
    assert {"query": {"match": {'f': 42}}} == s.to_dict()

    assert {"query": {"match": {'f': 42}}, "size": 10} == s.to_dict(size=10)

    s.aggs.bucket('per_tag', 'terms', field='f').aggregate('max_score', 'max', field='score')
    d = {
        'aggs': {
            'per_tag': {
                'terms': {'field': 'f'},
                'aggs': {'max_score': {'max': {'field': 'score'}}}
             }
        },
        'query': {'match': {'f': 42}}
    }
    assert d == s.to_dict()

def test_complex_example():
    s = search.Search()
    s = s.query('match', title='python') \
        .query(~Q('match', title='ruby')) \
        .filter(F('term', category='meetup') | F('term', category='conference')) \
        .post_filter('terms', tags=['prague', 'czech'])

    s.aggs.bucket('per_country', 'terms', field='country')\
        .aggregate('avg_attendees', 'avg', field='attendees')

    s.query.minimum_should_match = 2

    assert {
        'query': {
            'filtered': {
                'filter': {
                    'bool': {
                        'should': [
                            {'term': {'category': 'meetup'}},
                            {'term': {'category': 'conference'}}
                        ]
                    }
                },
                'query': {
                    'bool': {
                        'must': [ {'match': {'title': 'python'}}],
                        'must_not': [{'match': {'title': 'ruby'}}],
                        'minimum_should_match': 2
                    }
                }
            }
        },
        'post_filter': {
            'bool': {'must': [{'terms': {'tags': ['prague', 'czech']}}]}
        },
        'aggs': {
            'per_country': {
                'terms': {'field': 'country'},
                'aggs': {
                    'avg_attendees': {'avg': {'field': 'attendees'}}
                }
            }
        }
    } == s.to_dict()

def test_reverse():
    d =  {
        'query': {
            'filtered': {
                'filter': {
                    'bool': {
                        'should': [
                            {'term': {'category': 'meetup'}},
                            {'term': {'category': 'conference'}}
                        ]
                    }
                },
                'query': {
                    'bool': {
                        'must': [ {'match': {'title': 'python'}}],
                        'must_not': [{'match': {'title': 'ruby'}}],
                        'minimum_should_match': 2
                    }
                }
            }
        },
        'post_filter': {
            'bool': {'must': [{'terms': {'tags': ['prague', 'czech']}}]}
        },
        'aggs': {
            'per_country': {
                'terms': {'field': 'country'},
                'aggs': {
                    'avg_attendees': {'avg': {'field': 'attendees'}}
                }
            }
        }
    }

    s = search.Search.from_dict(d)

    assert d == s.to_dict()
