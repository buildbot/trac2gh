"""
code taken from https://github.com/hinnerk/Trac2Gollum
"""
import os
import re


def convert_code(text):
    """ replace code blocks (very primitive)

    >>> convert_code(u"\\nTest\\n\\n{{{\\n#!sh\\nCode paragraph\\n}}}\\n\\nTest\\n")
    u'\\nTest\\n\\n```sh\\nCode paragraph\\n```\\n\\nTest\\n'
    >>> convert_code(u"\\nTest\\n\\n{{{\\nCode paragraph\\n}}}\\n\\nTest\\n")
    u'\\nTest\\n\\n\\n    Code paragraph\\n\\n\\nTest\\n'

    """
    result = u""
    start = False
    running = False
    original = text
    indent = u""
    for line in text.splitlines():
        if line.strip() == u"{{{":
            start = True
            running = True
        elif start:
            start = False
            if line.startswith("#!"):
                result += u"```" + line.replace("#!", "") + os.linesep
            else:
                indent = u"    "
                result += os.linesep + indent + line + os.linesep
        elif line.strip() == u"}}}" and running:
            running = False
            if indent:
                indent = u""
                result += os.linesep
            else:
                result += u"```" + os.linesep
        else:
            result += indent + line + os.linesep

    if running:
        # something went wrong; don't touch the text.
        return original

    return result


re_macro = re.compile(r'\[{2}(\w+)\]{2}')
re_inlinecode = re.compile(r'\{\{\{([^\n]+?)\}\}\}')
re_h4 = re.compile(r'====\s(.+?)\s====')
re_h3 = re.compile(r'===\s(.+?)\s===')
re_h2 = re.compile(r'==\s(.+?)\s==')
re_h1 = re.compile(r'=\s(.+?)\s=')
re_uri = re.compile(r'\[(?:wiki:)?([^\s]+)\s(.+)\]')
re_wiki_uri = re.compile(r'(\s)wiki:([A-Za-z0-9]+)(\s)')
re_CamelCaseUri = re.compile(r'([^"\/\!\[\]\|])(([A-Z][a-z0-9]+){2,})')
re_NoUri = re.compile(r'\!(([A-Z][a-z0-9]+){2,})')
re_strong = re.compile(r"'''(.+)'''")
re_italic = re.compile(r"''(.+)''")
re_ul = re.compile(r'(^\s\*)', re.MULTILINE)
re_ol = re.compile(r'^\s(\d+\.)', re.MULTILINE)


def convert_text(text):
    """ converts trac wiki to gollum markdown syntax

    >>> format_text(u"= One =\\n== Two ==\\n=== Three ===\\n==== Four ====")
    u'# One\\n## Two\\n### Three\\n#### Four\\n'
    >>> format_text(u"Paragraph with ''italic'' and '''bold'''.")
    u'Paragraph with *italic* and **bold**.\\n'
    >>> format_text(u"Example with [wiki:a/b one link].")
    u'Example with [[one link|a/b]].\\n'
    >>> format_text(u"Beispiel mit [http://blog.fefe.de Fefes Blog] Link.")
    u'Beispiel mit [[Fefes Blog|http://blog.fefe.de]] Link.\\n'
    >>> format_text(u"Beispiel mit CamelCase Link.")
    u'Beispiel mit [[CamelCase]] Link.\\n'
    >>> format_text(u"Fieser [WarumBackup Argumente fuer dieses Angebot] Link")
    u'Fieser [[Argumente fuer dieses Angebot|WarumBackup]] Link\\n'
    >>> format_text(u"Beispiel ohne !CamelCase Link.")
    u'Beispiel ohne CamelCase Link.\\n'
    >>> format_text(u"Beispiel mit wiki:wikilink")
    u'Beispiel mit [[wikilink]]\\n'
    >>> format_text(u"Test {{{inline code}}}\\n\\nand more {{{inline code}}}.")
    u'Test `inline code`\\n\\nand more `inline code`.\\n'
    >>> format_text(u"\\n * one\\n * two\\n")
    u'\\n* one\\n* two\\n'
    >>> format_text(u"\\n 1. first\\n 2. second\\n")
    u'\\n1. first\\n2. second\\n'
    >>> format_text(u"There is a [[macro]] here.")
    u'There is a (XXX macro: "macro") here.\\n'
    """
    # TODO: ticket: and source: links are not yet handled
    text = convert_code(text)
    text = re_macro.sub(r'(XXX macro: "\1")', text)
    text = re_inlinecode.sub(r'`\1`', text)
    text = re_h4.sub(r'#### \1', text)
    text = re_h3.sub(r'### \1', text)
    text = re_h2.sub(r'## \1', text)
    text = re_h1.sub(r'# \1', text)
    text = re_uri.sub(r'[[\2|' + r'\1]]', text)
    text = re_CamelCaseUri.sub(r'\1[[\2]]', text)
    text = re_wiki_uri.sub(r'\1[[\2]]\3', text)
    text = re_NoUri.sub(r'\1', text)
    text = re_strong.sub(r'**\1**', text)
    text = re_italic.sub(r'*\1*', text)
    text = re_ul.sub(r'*', text)
    text = re_ol.sub(r'\1', text)
    return text
