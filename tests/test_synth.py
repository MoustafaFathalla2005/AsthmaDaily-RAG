from webapp import synthesize_answer

class DummyDoc:
    def __init__(self, text, name='DOC', page=1):
        self.page_content = text
        self.metadata = {'document_name': name, 'page_number': page}


def test_synthesize_simple_list():
    docs = [(DummyDoc('This is a guideline passage about inhaled steroids.'), 0.9),
            (DummyDoc('Follow-up recommendation: review inhaler technique.'), 0.8)]
    out = synthesize_answer(docs, max_chars=500)
    assert out and 'summary' in out and 'citations' in out
    assert len(out['citations']) >= 1


def test_synthesize_source_aware():
    src = {
        'GINA': [(DummyDoc('GINA guidance line.' , name='GINA', page=10), 0.9)],
        'WHO': [(DummyDoc('WHO child-specific note.', name='WHO', page=5), 0.8)]
    }
    out = synthesize_answer(src)
    assert isinstance(out, dict)
    assert 'GINA' in out and 'WHO' in out
    assert 'summary' in out['GINA'] and 'citations' in out['WHO']
