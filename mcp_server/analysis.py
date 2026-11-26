"""Deterministic prose diagnostics for journalism drafts.

Every check in this module works on surface text. None of them can decide
whether a claim is true, whether a quotation is faithful to a recording this
server has not seen, or whether a story is good. They exist so a model can test
its own draft cheaply and repeatedly instead of guessing, and so a human editor
can see exactly what was flagged.

A draft may be in English or Filipino/Tagalog. The pattern lists carry both, so
a single scan catches "in today's fast-paced world" and "sa kasalukuyang
panahon" alike, and a mixed draft needs no language switch. The rhythm and
morphology statistics (adverbs in -ly, auxiliary passives, English nominalizing
suffixes) are shaped by English, so on a Filipino draft read them as rough
signals rather than as counts.

Two rules follow from that and are repeated in every tool response:

1. A finding is a prompt to look, not a verdict. Zero findings is not a pass.
2. Presence in supplied notes is not support, and absence is not falsity.
"""

from __future__ import annotations

import difflib
import re
import statistics
from typing import Any, Iterable

WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F0-9'\u2019\-]+")
_ABBREV = (
    r"(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|No|vs|etc|e\.g|i\.e|U\.S|A\.M|P\.M|a\.m|p\.m"
    r"|Inc|Corp|Ltd|Gov|Sen|Rep|Gen|Col|Lt|Capt|Sgt|Fr|Rev|Hon|Msgr|Atty|Engr"
    r"|Brgy|Dept|Est|approx|Fig|Vol|Ch|pp|No)"
)
_ABBREV_RE = re.compile(r"\b" + _ABBREV + r"\.", re.IGNORECASE)
_SENT_SPLIT_RE = re.compile(
    r"(?<=[.!?\u2026])\s+(?=[\"\u201c'\u2018(\[]?[A-Z\u00C0-\u00DE0-9])"
)
_PASSIVE_RE = re.compile(
    r"\b(?:was|were|is|are|been|being|be)\s+(?:\w+ly\s+)?(\w+(?:ed|en))\b",
    re.IGNORECASE,
)
_ADVERB_RE = re.compile(r"\b\w{4,}ly\b", re.IGNORECASE)
_NOMINAL_RE = re.compile(
    r"\b\w{5,}(?:tion|sion|ment|ance|ence|ity|ness|ization|isation"
    r"|asyon|idad|mento|ismo)\b",
    re.IGNORECASE,
)
_CONTRACTION_RE = re.compile(
    r"\b(?:can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|it's"
    r"|that's|there's|I'm|I've|I'd|I'll|you're|we're|they're|we've|they've"
    r"|couldn't|wouldn't|shouldn't|hasn't|haven't|hadn't|let's)\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(
    r"(?<![\w.])(?:\d{1,2}:\d{2}(?:\s?[ap]\.?m\.?)?|(?:[\u20B1$]|PHP|US\$)?\s?\d[\d,]*(?:\.\d+)?\s?(?:%|percent)?)(?![\w.])"
)
_NAME_RE = re.compile(
    r"\b(?:[A-Z\u00C0-\u00DE][\w'\u2019\-]+"
    r"(?:\s+(?:[A-Z\u00C0-\u00DE][\w'\u2019\-]+|of|de|del|dela|van|der|ng|y))){1,4}\b"
)
_QUOTE_RE = re.compile(
    r"[\u201c\"]([^\u201c\u201d\"\n]{2,500})[\u201d\"]|[\u2018']([^\u2018\u2019'\n]{2,500})[\u2019']"
)

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_NAME_STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "for", "but", "and", "or", "however",
    "after", "before", "when", "while", "he", "she", "they", "it", "we", "you",
    "i", "this", "that", "these", "those", "there", "his", "her", "their",
    "its", "our", "my", "mr", "mrs", "ms", "dr", "prof", "sir", "ma'am",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december", "section",
    "chapter", "part", "story", "photo", "editor",
    # Filipino/Tagalog sentence starters, function words, days, and months. They
    # are capitalized for position, not because they name anyone; without these
    # entries check_facts reports each one as a name missing from the notes.
    "ang", "si", "sina", "sa", "mga", "ng", "siya", "sila", "ito", "iyan", "iyon", "at",
    "o", "ngunit", "pero", "subalit", "datapwat", "samantala", "gayunpaman",
    "gayon", "dahil", "sapagkat", "kaya", "kung", "para", "mula", "hanggang",
    "matapos", "bago", "habang", "noong", "ngayon", "bukas", "kahapon",
    "bawat", "lahat", "ilan", "isang", "may", "mayroon", "mayroong", "bilang",
    "ayon", "bukod", "dagdag", "higit", "sabi", "sinabi", "tila", "dito",
    "doon", "maging", "gaya", "tulad", "tungkol", "ukol",
    "lunes", "martes", "miyerkules", "huwebes", "biyernes", "sabado", "linggo",
    "enero", "pebrero", "marso", "abril", "mayo", "hunyo", "hulyo", "agosto",
    "setyembre", "oktubre", "nobyembre", "disyembre",
}

_QUALIFIERS = (
    "may", "might", "could", "can", "alleged", "allegedly", "according to",
    "if", "up to", "about", "more than", "less than", "at least", "nearly",
    "reportedly", "said", "says", "denied", "estimated", "roughly",
    # Filipino/Tagalog qualifiers. Hedges are where an edit most often raises
    # certainty: dropping "di-umano", "raw", or "maaari" turns a report into a
    # fact, so diff_meaning must count them too.
    "maaari", "maaaring", "posible", "posibleng", "ayon kay", "ayon sa", "di-umano",
    "umano", "raw", "daw", "sinabi", "sinasabi", "pinabulaanan", "tinatayang",
    "halos", "mahigit", "hindi bababa sa", "kung", "tila", "marahil",
)

# Word-bounded so short Filipino qualifiers ("raw", "kung", "daw") are not
# counted inside unrelated words.
_QUALIFIER_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(q) for q in sorted(_QUALIFIERS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _rule(
    rule_id: str,
    pattern: str,
    label: str,
    severity: str,
    note: str,
    fix: str,
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "pattern": re.compile(pattern, re.IGNORECASE),
        "label": label,
        "severity": severity,
        "note": note,
        "fix": fix,
    }


SLOP_RULES: tuple[dict[str, Any], ...] = (
    _rule(
        "ai-opener",
        r"\bin today'?s (?:fast-?paced|modern|digital|hyper-?connected|competitive|world|society|age)\b"
        r"|\bas we (?:all )?know\b|\bin a world where\b|\bsince the dawn of time\b"
        r"|\bsa kasalukuyang? (?:panahon|henerasyon)\b"
        r"|\bsa (?:makabago|moderno)ng (?:panahon|mundo|henerasyon)\b"
        r"|\bsa panahon ngayon\b|\bsa mundong ito\b|\bsa ating lipunan\b"
        r"|\btulad ng alam nating lahat\b|\bhindi na bago sa (?:atin|amin|kanila)\b"
        r"|\bsa gitna ng mabilis na pagbabago\b|\bsa bawat isa sa atin\b",
        "Formulaic opener",
        "high",
        "Announces the topic instead of reporting it. This is the single most reliable machine-writing tell.",
        "Start on a reported moment, detail, fact, or question from the notes.",
    ),
    _rule(
        "slop-phrase",
        r"\bdelve(?:s|d|ing)? into\b"
        r"|\btapestry of\b"
        r"|\bnavigat(?:e|ing|ed) the (?:complexities|complexity|challenges|landscape|nuances)\b"
        r"|\ba testament to\b|\bstands? as a\b"
        r"|\bplays? a (?:crucial|vital|pivotal|key) role\b"
        r"|\bnot only\b[^.!?]{0,90}\bbut also\b"
        r"|\bit(?:'s| is) (?:important|worth|essential) to (?:note|remember|understand)\b"
        r"|\b(?:ever-evolving|ever-changing|ever-growing)\b"
        r"|\bunlock(?:s|ing|ed)? the (?:potential|power|secrets)\b"
        r"|\bgame[- ]changer\b"
        r"|\b(?:myriad|plethora) of\b"
        r"|\bwhen it comes to\b"
        r"|\bbeacon of (?:hope|light)\b"
        r"|\bembark(?:s|ing|ed)? on a journey\b"
        r"|\bdawn of a new era\b"
        r"|\bthe (?:realm|landscape) of\b"
        r"|\bin conclusion\b|\bat the end of the day\b"
        r"|\bnagsisilbing (?:susi|daan|tulay|testamento|sagisag|paalala)\b"
        r"|\bgumaganap ng (?:mahalaga|kritikal|pangunahin)ng papel\b"
        r"|\bmahalagang (?:tandaan|malaman|mapagtanto)\b"
        r"|\bsusi (?:sa|ng) tagumpay\b"
        r"|\bhindi lamang\b[^.!?]{0,90}\bkundi (?:pati )?rin\b"
        r"|\bsa (?:larangan|aspeto) ng\b"
        r"|\bnagbibigay-diin sa kahalagahan\b|\bnagpapakita ng (?:kahalagahan|potensyal)\b"
        r"|\bpatuloy na (?:umuunlad|lumalago|umusbong)\b"
        r"|\bbagong (?:yugto|panahon|kabanata)\b|\bsa kabila ng mga hamon\b"
        r"|\bliwanag ng pag-asa\b|\bsa dakong huli\b",
        "Slop phrase",
        "high",
        "Stock phrasing that carries no reported information and reads as machine-generated.",
        "Delete it and state the specific fact it was standing in for. If there is no fact, the sentence has no story.",
    ),
    _rule(
        "pseudo-profundity",
        r"\bwhat happened next\b|\bthe rest is history\b|\bonly time will tell\b"
        r"|\bone thing is certain\b|\ba (?:story|tale) of\b|\blittle did\b"
        r"|\bwould change (?:everything|their lives) forever\b"
        r"|\bang natitira(?: lamang)? ay kasaysayan\b"
        r"|\bpanahon lamang ang (?:makapagsasabi|magsasabi)\b|\bisang bagay ang tiyak\b"
        r"|\bbabaguhin (?:nito )?ang (?:lahat|kanyang buhay|kanilang buhay)(?: magpakailanman)?\b",
        "Pseudo-profound filler",
        "high",
        "Signals a manufactured turn the reporting may not support.",
        "Replace with the actual consequence, or cut the promise and trust the material.",
    ),
    _rule(
        "invented-interiority",
        r"\bfelt a (?:wave|pang|surge|rush)\b|\ba wave of \w+ (?:washed|swept)\b"
        r"|\bcould(?:n't| not) help but\b|\btears (?:welled|filled|streamed)\b"
        r"|\b(?:his|her|their) heart (?:sank|raced|pounded|ached)\b"
        r"|\bthought to (?:himself|herself|themselves)\b"
        r"|\bseemed to (?:know|understand|sense|realize)\b"
        r"|\bwondered aloud\b"
        r"|\bnakaramdam (?:siya |sila )?ng (?:kaba|takot|lungkot|galit|pag-asa|hiya)\b"
        r"|\bnaramdaman (?:niya|nila) ang\b"
        r"|\bnaisip (?:niya|nila) (?:sa kanyang sarili|sa kanilang sarili)\b"
        r"|\bkumalabog ang (?:kanyang |kanilang )?(?:puso|dibdib)\b|\bpumintig ang (?:kanyang )?puso\b"
        r"|\bnapuno ng (?:kaba|takot|pag-asa|lungkot) ang (?:kanyang )?(?:dibdib|puso)\b"
        r"|\btumulo ang (?:kanyang )?luha\b|\bhindi (?:niya|nila) mapigilan ang\b"
        r"|\btila (?:alam|batid|ramdam) (?:na )?(?:niya|nila)\b|\bnag-isip (?:siya )?nang malalim\b",
        "Invented interiority",
        "high",
        "A reporter cannot observe feelings or thoughts. This only belongs if it is a direct quotation or documented in the notes.",
        "Keep it only with a quotation, recording, or written note. Otherwise cut it or attribute it explicitly.",
    ),
    _rule(
        "invented-reaction",
        r"\beyes (?:lit up|widened|welled|sparkled)\b"
        r"|\bsmiled (?:knowingly|warmly|softly|sadly)\b"
        r"|\bnodded (?:slowly|knowingly|thoughtfully)\b"
        r"|\bvoice (?:trembling|cracking|breaking|quivering)\b"
        r"|\blet out a (?:sigh|breath|laugh|gasp)\b"
        r"|\bshifted (?:uncomfortably|nervously)\b|\bfidgeted\b"
        r"|\bkumislap ang (?:kanyang )?mga mata\b|\blumiwanag ang (?:kanyang )?mukha\b"
        r"|\bngumiti (?:siya )?nang (?:mapait|malungkot|malambing|mahina)\b"
        r"|\btumango (?:siya )?nang (?:dahan-dahan|mabagal|malumanay)\b"
        r"|\bnanginginig ang (?:kanyang )?boses\b|\bpumiyok ang (?:kanyang )?boses\b"
        r"|\bbumuntong-hininga\b|\bnapailing (?:siya)?\b",
        "Inferred physical reaction",
        "high",
        "Micro-observations are usually reconstructed from memory hours later. Verify against notes before keeping.",
        "Cite the observation in your notes, or describe only what was recorded (what was said, what was done).",
    ),
    _rule(
        "unsupported-scene",
        r"\bthe (?:crowd|room|hall|cafeteria|classroom|audience) (?:erupted|fell silent|went silent|gasped)\b"
        r"|\ba hush fell\b|\bthe air was thick\b|\btime seemed to (?:stop|slow)\b"
        r"|\byou could (?:hear|feel) (?:a pin drop|the tension)\b"
        r"|\b(?:biglang )?natahimik ang (?:lahat|buong bulwagan|bulwagan|silid|klase|madla)\b"
        r"|\bnaghiyawan ang (?:mga tao|madla|mga estudyante|karamihan)\b"
        r"|\bmakapal ang (?:hanging|hangin)\b|\bnamayani ang (?:katahimikan|tensyon)\b"
        r"|\b(?:para bang |tila )?tumigil ang oras\b"
        r"|\bdinig mo (?:ang pagbagsak ng karayom|ang tensyon)\b|\bramdam mo ang tensyon\b",
        "Generic scene beat",
        "high",
        "Scene shorthand that implies observation the draft has not demonstrated.",
        "Use one concrete, recorded detail from the scene instead of the stock beat.",
    ),
    _rule(
        "unsourced-attribution",
        r"\b(?:experts|critics|analysts|officials|sources|observers|many|some|people|students|teachers)"
        r"\s+(?:say|said|says|believe|believes|claim|claims|argue|argues|fear|fears|worry|worries|agree|agrees)\b"
        r"|\bit is (?:believed|said|widely known)\b|\bstudies (?:show|suggest|say)\b"
        r"|\bresearch (?:shows|suggests|says)\b"
        r"|\bayon sa (?:mga )?(?:eksperto|opisyal|analista|tagapagmasid|guro|estudyante|magulang|pinuno)\b"
        r"|\b(?:sinabi|sinasabi|sabi) ng mga (?:eksperto|opisyal|analista|guro|estudyante|tao)\b"
        r"|\b(?:marami|ilan|karamihan) ang (?:nagsasabi|naniniwala|nag-aalala|umaasa)\b"
        r"|\bpinaniniwalaan ng (?:marami|karamihan|mga tao)\b"
        r"|\bbatay sa (?:mga )?pag-aaral\b|\bipinapakita ng (?:mga )?pananaliksik\b",
        "Unattributed claim",
        "high",
        "No named person or document. An editor cannot verify it, and the reader cannot weigh it.",
        "Name the source and their role, or say why anonymity was granted and who approved it.",
    ),
    _rule(
        "mechanical-transition",
        r"(?:^|[.!?]\s+)(?:furthermore|moreover|additionally|in addition|thus|hence|therefore"
        r"|higit pa rito|bukod dito|dagdag pa(?: rito)?|samakatuwid|sa madaling salita)\b",
        "Mechanical transition",
        "medium",
        "Paragraph glue that does not explain the relationship between ideas.",
        "Cut it, or name the actual relation (because, but, even so, three weeks later).",
    ),
    _rule(
        "inflated-word",
        r"\butiliz(?:e|es|ed|ing)\b|\bleverag(?:e|es|ed|ing)\b|\bfacilitat(?:e|es|ed|ing)\b"
        r"|\bcommenc(?:e|es|ed|ing)\b|\bendeavor(?:s|ed|ing)?\b|\bascertain(?:s|ed|ing)?\b"
        r"|\bprior to\b|\bsubsequent to\b|\bdue to the fact that\b|\bin order to\b"
        r"|\bat this point in time\b|\bin the event that\b|\ba large number of\b"
        r"|\bthe majority of\b"
        r"|\bsa kadahilanang\b|\bdahil sa katotohanan na\b|\bupang maisakatuparan\b"
        r"|\bmalaki(?:ng)? bilang ng\b",
        "Inflated wording",
        "medium",
        "Longer word, same meaning. Plain verbs read faster and sound like a person.",
        "Use the plain equivalent: use, help, start, try, find out, before, after, because, to, now, if, many, most.",
    ),
    _rule(
        "hedge-stack",
        r"\b(?:may|might|could) (?:possibly|potentially|conceivably)\b"
        r"|\bseems? to (?:suggest|indicate|imply)\b|\bappears? to (?:suggest|indicate)\b"
        r"|\bsomewhat\b|\bto some extent\b|\bin some ways\b"
        r"|\bmaaaring (?:posible|posibleng)\b|\bposibleng maaari\b"
        r"|\btila (?:nagpapahiwatig|nagpapakita) na\b"
        r"|\bsa (?:ilang|isang tiyak na) paraan\b|\bsa paanuman\b",
        "Stacked hedging",
        "high",
        "Double qualifications blur what is actually known.",
        "Keep the one qualifier the evidence supports and delete the rest.",
    ),
    _rule(
        "intensifier",
        r"\b(?:very|really|quite|extremely|incredibly|truly|literally|basically|actually|definitely|absolutely)\b"
        r"|\b(?:sobrang|talagang|talaga|lubos|lubhang|tunay na|ganap na)\b|\bnapaka\w+\b",
        "Empty intensifier",
        "medium",
        "The intensifier does the work the detail should do.",
        "Replace with the measurement or detail: how many, how long, how loud, compared with what.",
    ),
    _rule(
        "editorializing",
        r"\b(?:clearly|obviously|of course|needless to say|sadly|thankfully|unfortunately)\b"
        r"|\bsa (?:kasamaang|kabutihang) palad\b|\bsiyempre\b|\bwalang duda\b"
        r"|\bmalinaw na malinaw\b|\bhindi mapag-aalinlanganan\b|\bkapansin-pansin\b",
        "Editorializing",
        "medium",
        "Tells the reader how to feel instead of giving them the evidence.",
        "Cut it and let the reported fact carry the judgment, or move the judgment into an attributed quotation.",
    ),
    _rule(
        "loaded-adjective",
        r"\b(?:shocking|heartbreaking|heartwarming|devastating|tragic|unbelievable|horrific|dire|grim)\b"
        r"|\bnakakagulat\b|\bnakakalungkot\b|\bnakakadurog-puso\b"
        r"|\bkahindik-hindik\b|\bkagila-gilalas\b|\bkamangha-mangha\b",
        "Loaded adjective",
        "medium",
        "Evaluative language in the reporter's voice weakens credibility.",
        "Replace with the specific fact that produced the reaction.",
    ),
    _rule(
        "news-cliche",
        r"\bshed(?:s|ding)? light on\b|\bin the wake of\b|\bsent shockwaves\b"
        r"|\bbustling\b|\bnestled\b|\bboasts? (?:a|an|the)\b|\ba slew of\b"
        r"|\bsparked (?:outrage|debate|concern)\b|\bamid (?:growing )?(?:concern|outcry)\b"
        r"|\bsa gitna ng\b|\bnagsilbing saksi\b|\bpinukaw ang atensyon\b"
        r"|\bnagbabadya ng pagbabago\b|\bmakulay na (?:pagdiriwang|karanasan)\b"
        r"|\bmakasaysayang (?:pangyayari|sandali)\b|\bhindi matatawaran\b",
        "News cliché",
        "medium",
        "Overused newsroom shorthand; readers skim past it.",
        "Say what happened in specific terms.",
    ),
    _rule(
        "vague-quantifier",
        r"\b(?:a lot of|lots of|plenty of|a number of|several|numerous|various|many)\b"
        r"|\b(?:marami(?:ng)?|napakarami|ilang|sari-saring|iba't ibang|kakaunti)\b",
        "Vague quantity",
        "low",
        "A count exists or it does not; vague quantifiers hide which.",
        "Give the number with its scope, or say plainly that no count is available.",
    ),
    _rule(
        "exclamation",
        r"!",
        "Exclamation mark",
        "low",
        "Rarely appropriate outside quotations in news copy.",
        "Remove it, or confirm it is inside a quotation.",
    ),
)


def _sentences(text: str) -> list[str]:
    protected = _ABBREV_RE.sub(lambda m: m.group(0)[:-1] + "\u0000", text)
    parts = _SENT_SPLIT_RE.split(protected)
    return [p.replace("\u0000", ".").strip() for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _line_at(text: str, index: int) -> int:
    return text.count("\n", 0, max(0, index)) + 1


def _excerpt(text: str, start: int, end: int, pad: int = 55) -> str:
    raw = text[max(0, start - pad) : end + pad]
    return re.sub(r"\s+", " ", raw).strip()


def _per_1000(count: int, words: int) -> float:
    return round(count * 1000.0 / words, 1) if words else 0.0


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return round(statistics.pstdev(values), 1)


def _findings_for_rules(text: str, max_per_rule: int = 3) -> tuple[list[dict], dict[str, int]]:
    findings: list[dict] = []
    counts: dict[str, int] = {}
    for rule in SLOP_RULES:
        matches = list(rule["pattern"].finditer(text))
        if not matches:
            continue
        counts[rule["id"]] = len(matches)
        for m in matches[:max_per_rule]:
            findings.append(
                {
                    "rule": rule["id"],
                    "label": rule["label"],
                    "severity": rule["severity"],
                    "line": _line_at(text, m.start()),
                    "match": re.sub(r"\s+", " ", m.group(0)).strip(),
                    "excerpt": _excerpt(text, m.start(), m.end()),
                    "note": rule["note"],
                    "fix": rule["fix"],
                }
            )
    return findings, counts


def _rhythm_findings(text: str, stats: dict[str, Any], sentences: list[str]) -> list[dict]:
    findings: list[dict] = []

    if len(sentences) >= 8 and stats["sentence_length_stdev"] < 4.0:
        findings.append(
            {
                "rule": "monotonous-rhythm",
                "label": "Uniform sentence rhythm",
                "severity": "medium",
                "line": 1,
                "match": f"{len(sentences)} sentences, stdev {stats['sentence_length_stdev']} words",
                "excerpt": sentences[0][:160],
                "note": "Sentences of nearly identical length read as a list, not as prose.",
                "fix": "Break one long sentence in two and fold a short one into a longer clause; vary where the main verb lands.",
            }
        )

    if stats["sentences_over_40_words"]:
        long_ones = [s for s in sentences if len(_words(s)) > 40][:2]
        findings.append(
            {
                "rule": "run-on-sentence",
                "label": "Overlong sentence",
                "severity": "medium",
                "line": 1,
                "match": f"{stats['sentences_over_40_words']} sentence(s) over 40 words",
                "excerpt": long_ones[0][:200] if long_ones else "",
                "note": "Readers lose the subject across a long clause chain.",
                "fix": "Split at the second clause boundary; keep the reporting in one clause per sentence.",
            }
        )

    if stats["avg_paragraph_words"] > 110:
        findings.append(
            {
                "rule": "long-paragraph",
                "label": "Dense paragraph",
                "severity": "low",
                "line": 1,
                "match": f"average {stats['avg_paragraph_words']} words per paragraph",
                "excerpt": "",
                "note": "Long unbroken blocks are hard to scan on phones.",
                "fix": "Break where the topic or the speaker changes.",
            }
        )

    if len(sentences) >= 6:
        openers: dict[str, int] = {}
        for s in sentences:
            w = _words(s)
            if w:
                openers[w[0].lower()] = openers.get(w[0].lower(), 0) + 1
        neutral_openers = {
            "the", "a", "an", "he", "she", "it", "they", "i", "we", "but", "and",
            "ang", "si", "sina", "siya", "sila", "ito", "at", "ngunit", "pero",
            "sa", "noong", "dahil", "kaya", "may", "para", "habang", "matapos",
        }
        repeated = sorted(
            ((k, v) for k, v in openers.items() if v >= 3 and k not in neutral_openers),
            key=lambda kv: -kv[1],
        )
        if repeated:
            findings.append(
                {
                    "rule": "repeated-opener",
                    "label": "Repeated sentence opener",
                    "severity": "low",
                    "line": 1,
                    "match": f"{repeated[0][0]!r} starts {repeated[0][1]} sentences",
                    "excerpt": "",
                    "note": "Parallel openings flatten the paragraph.",
                    "fix": "Rebuild one of them around its object or a time marker.",
                }
            )

    if stats["adverbs_per_1000"] > 18:
        findings.append(
            {
                "rule": "adverb-density",
                "label": "Heavy adverb use",
                "severity": "medium",
                "line": 1,
                "match": f"{stats['adverbs_per_1000']} -ly adverbs per 1,000 words",
                "excerpt": "",
                "note": "Adverbs usually prop up a weak verb choice.",
                "fix": "Replace verb + adverb with one precise verb.",
            }
        )

    if stats["passive_per_1000"] > 12:
        findings.append(
            {
                "rule": "passive-density",
                "label": "Passive constructions",
                "severity": "low",
                "line": 1,
                "match": f"{stats['passive_per_1000']} per 1,000 words (heuristic)",
                "excerpt": "",
                "note": "Passive voice hides who acted. Sometimes that is correct (unknown actor, victim focus).",
                "fix": "Name the actor where it is known and the reader needs it.",
            }
        )

    if stats["nominalizations_per_1000"] > 28:
        findings.append(
            {
                "rule": "nominalization-density",
                "label": "Nominalized prose",
                "severity": "medium",
                "line": 1,
                "match": f"{stats['nominalizations_per_1000']} abstract nouns per 1,000 words",
                "excerpt": "",
                "note": "Actions turned into abstract nouns drain the sentence of people and verbs.",
                "fix": "Turn the noun back into a verb and give it a subject.",
            }
        )

    if stats["emdashes_per_1000"] > 6:
        findings.append(
            {
                "rule": "em-dash-overuse",
                "label": "Em-dash overuse",
                "severity": "low",
                "line": 1,
                "match": f"{stats['emdashes_per_1000']} per 1,000 words",
                "excerpt": "",
                "note": "Heavy em-dash use is a common machine-writing habit.",
                "fix": "Use a comma, a full stop, or restructure the aside.",
            }
        )

    return findings


def analyze_prose(
    text: str,
    mode: str = "feature",
    voice_sample: str | None = None,
    max_findings: int = 40,
) -> dict[str, Any]:
    """Return deterministic craft diagnostics for a draft."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")

    sentences = _sentences(text)
    words = _words(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    lengths = [len(_words(s)) for s in sentences if _words(s)]
    word_count = len(words)

    stats = {
        "words": word_count,
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "avg_sentence_words": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "sentence_length_stdev": _stdev(lengths),
        "longest_sentence_words": max(lengths) if lengths else 0,
        "sentences_over_40_words": sum(1 for n in lengths if n > 40),
        "avg_paragraph_words": round(word_count / len(paragraphs), 1) if paragraphs else 0.0,
        "adverbs_per_1000": _per_1000(len(_ADVERB_RE.findall(text)), word_count),
        "passive_per_1000": _per_1000(len(_PASSIVE_RE.findall(text)), word_count),
        "nominalizations_per_1000": _per_1000(len(_NOMINAL_RE.findall(text)), word_count),
        "contractions": len(_CONTRACTION_RE.findall(text)),
        "emdashes_per_1000": _per_1000(text.count("\u2014") + text.count(" - "), word_count),
    }

    findings, counts = _findings_for_rules(text)
    findings.extend(_rhythm_findings(text, stats, sentences))
    findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 3), f["rule"], f["line"]))

    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    low = sum(1 for f in findings if f["severity"] == "low")

    rationale: list[str] = []
    if high:
        rationale.append(f"{high} high-severity pattern(s): fabricated-sounding detail or machine phrasing.")
    if stats["sentence_length_stdev"] and stats["sentence_length_stdev"] < 4.0 and len(sentences) >= 8:
        rationale.append("Sentence lengths barely vary, so the prose reads mechanically.")
    if not findings:
        rationale.append("No configured pattern fired. That is not a pass: read the draft for claim support and quotation fidelity.")

    if high >= 3 or (len(sentences) >= 8 and stats["sentence_length_stdev"] < 4.0 and high >= 1):
        signal = "mechanical"
    elif not high and not medium:
        signal = "clear"
    else:
        signal = "mixed"

    result: dict[str, Any] = {
        "mode": mode,
        "stats": stats,
        "findings": findings[:max_findings],
        "finding_counts": counts,
        "severity_totals": {"high": high, "medium": medium, "low": low},
        "signal": signal,
        "signal_rationale": rationale,
        "disclaimer": (
            "Surface-pattern diagnostics only. This tool cannot verify a fact, a quotation, or quality; "
            "it cannot score a contest entry. Use it to find passages worth a second look, then apply the "
            "skill workflow and a human editor's judgment."
        ),
    }
    if voice_sample and voice_sample.strip():
        result["voice_comparison"] = compare_voice(voice_sample, text)
    return result


def _voice_profile(text: str) -> dict[str, Any]:
    sentences = _sentences(text)
    lengths = [len(_words(s)) for s in sentences if _words(s)]
    words = _words(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    return {
        "avg_sentence_words": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "sentence_length_stdev": _stdev(lengths),
        "adverbs_per_1000": _per_1000(len(_ADVERB_RE.findall(text)), len(words)),
        "contractions_per_1000": _per_1000(len(_CONTRACTION_RE.findall(text)), len(words)),
        "first_person_per_1000": _per_1000(
            len(re.findall(r"\b(?:I|we|our|us|my)\b", text)), len(words)
        ),
        "avg_word_length": round(
            sum(len(w) for w in words) / len(words), 2
        ) if words else 0.0,
        "avg_paragraph_words": round(len(words) / len(paragraphs), 1) if paragraphs else 0.0,
    }


def compare_voice(sample: str, draft: str) -> dict[str, Any]:
    """Describe measured differences between a voice sample and the draft."""
    a = _voice_profile(sample)
    b = _voice_profile(draft)
    deltas = {k: round(b[k] - a[k], 1) for k in a}
    notes = []
    if abs(deltas["avg_sentence_words"]) >= 3:
        notes.append(
            f"Sentence length differs by {deltas['avg_sentence_words']:+.1f} words on average."
        )
    if abs(deltas["contractions_per_1000"]) >= 6:
        notes.append(
            f"Contraction rate differs by {deltas['contractions_per_1000']:+.1f} per 1,000 words; "
            "the sample's formality is not being matched."
        )
    if abs(deltas["adverbs_per_1000"]) >= 6:
        notes.append("Adverb density does not match the sample.")
    if not notes:
        notes.append("Measured rhythm is close to the sample.")
    return {
        "sample": a,
        "draft": b,
        "deltas": deltas,
        "notes": notes,
        "disclaimer": (
            "A statistical proxy for rhythm and formality, not a voice imitation model. "
            "Never copy the sample's facts, phrasings, or identifiers; match only the measured shape."
        ),
    }


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    out: list[str] = []
    index: list[int] = []
    pending_space = False
    for i, ch in enumerate(text):
        mapped = ch
        if ch in "\u201c\u201d":
            mapped = '"'
        elif ch in "\u2018\u2019":
            mapped = "'"
        if mapped.isspace():
            pending_space = True
            continue
        if pending_space and out:
            out.append(" ")
            index.append(i)
        pending_space = False
        out.append(mapped.lower())
        index.append(i)
    return "".join(out), index


def _word_diff(draft_span: str, source_span: str) -> list[dict[str, str]]:
    a = draft_span.split()
    b = source_span.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ops.append(
            {
                "op": tag,
                "in_draft": " ".join(a[i1:i2]),
                "in_source": " ".join(b[j1:j2]),
            }
        )
    return ops


def _locate(quote_norm: str, source_norm: str) -> dict[str, Any] | None:
    """Find the best source window for a normalized quotation."""
    direct = source_norm.find(quote_norm)
    if direct != -1:
        return {"start": direct, "end": direct + len(quote_norm), "coverage": 1.0, "exact": True}

    words = quote_norm.split()
    best: dict[str, Any] | None = None
    for n in (8, 6, 4, 3):
        if len(words) < n:
            continue
        for i in range(0, len(words) - n + 1):
            shingle = " ".join(words[i : i + n])
            pos = source_norm.find(shingle)
            if pos == -1:
                continue
            prefix = len(" ".join(words[:i]))
            align = pos - prefix
            win_start = max(0, align - 150)
            win_end = min(len(source_norm), align + len(quote_norm) + 150)
            window = source_norm[win_start:win_end]
            sm = difflib.SequenceMatcher(None, quote_norm, window, autojunk=False)
            block = sm.find_longest_match(0, len(quote_norm), 0, len(window))
            coverage = round(block.size / max(1, len(quote_norm)), 3)
            if best is None or coverage > best["coverage"]:
                span_start = max(0, win_start + block.b - block.a)
                best = {
                    "start": span_start,
                    "end": min(len(source_norm), span_start + len(quote_norm)),
                    "coverage": coverage,
                    "exact": False,
                }
            if best is not None and best["coverage"] >= 0.999:
                return best
    return best


def check_quotes(
    draft: str, source_text: str, min_similarity: float = 0.6
) -> dict[str, Any]:
    """Locate every direct quotation in the supplied source material."""
    if not draft.strip():
        raise ValueError("draft must be non-empty")
    if not source_text.strip():
        raise ValueError("source_text must be non-empty (the notes, transcript, or document to compare against)")

    source_norm, source_map = _normalize_with_map(source_text)
    results: list[dict[str, Any]] = []

    for m in _QUOTE_RE.finditer(draft):
        raw = m.group(1) or m.group(2) or ""
        quote = re.sub(r"\s+", " ", raw).strip()
        if len(_words(quote)) < 2:
            continue
        quote_norm, _ = _normalize_with_map(quote)
        entry: dict[str, Any] = {
            "quote": quote,
            "line": _line_at(draft, m.start()),
            "short": len(_words(quote)) < 4,
            "status": "not_found",
            "similarity": 0.0,
            "source_line": None,
            "source_span": "",
            "differences": [],
        }
        hit = _locate(quote_norm, source_norm)
        if hit:
            last_index = max(0, len(source_map) - 1)
            start = min(hit["start"], last_index)
            end = max(start + 1, min(hit["end"], len(source_map)))
            span = source_text[source_map[start] : source_map[min(end, last_index)] + 1] if source_map else ""
            entry["similarity"] = hit["coverage"]
            entry["source_line"] = _line_at(source_text, source_map[start]) if source_map else None
            entry["source_span"] = re.sub(r"\s+", " ", span).strip()
            if hit["exact"]:
                entry["status"] = "exact"
            elif hit["coverage"] >= min_similarity:
                entry["status"] = "altered"
                entry["differences"] = _word_diff(quote, entry["source_span"])
            else:
                entry["status"] = "not_found"
        results.append(entry)

    summary = {
        "quotes_checked": len(results),
        "exact": sum(1 for r in results if r["status"] == "exact"),
        "altered": sum(1 for r in results if r["status"] == "altered"),
        "not_found": sum(1 for r in results if r["status"] == "not_found"),
    }
    return {
        "quotes": results,
        "summary": summary,
        "handling": (
            "`altered` means the words in the draft differ from the supplied material: keep the source wording "
            "or convert to a clearly attributed indirect paraphrase. `not_found` means the supplied material does "
            "not contain it: mark the quotation UNCHECKED and obtain the recording or note. It is not evidence "
            "of fabrication."
        ),
        "disclaimer": (
            "Compares against the text you supplied only. If the source material is incomplete, a not-found "
            "quotation is a missing record, not a false one."
        ),
    }


def _extract_numbers(text: str) -> list[str]:
    found: list[str] = []
    for m in _NUMBER_RE.finditer(text):
        token = re.sub(r"\s+", "", m.group(0))
        if token and any(ch.isdigit() for ch in token):
            found.append(token)
    return found


def _extract_names(text: str) -> list[str]:
    names: list[str] = []
    for m in _NAME_RE.finditer(text):
        candidate = m.group(0).strip()
        tokens = candidate.split()
        if not tokens:
            continue
        if tokens[0].lower() in _NAME_STOPWORDS:
            continue
        if len(" ".join(tokens)) < 3:
            continue
        if candidate not in names:
            names.append(candidate)
    return names


def check_facts(draft: str, source_text: str) -> dict[str, Any]:
    """Report which numbers and names in the draft appear in the supplied material."""
    if not draft.strip():
        raise ValueError("draft must be non-empty")
    if not source_text.strip():
        raise ValueError("source_text must be non-empty")

    source_norm, _ = _normalize_with_map(source_text)

    numbers = _extract_numbers(draft)
    names = _extract_names(draft)

    missing_numbers = []
    for token in numbers:
        norm = token.lower().replace(",", "")
        if norm not in source_norm.replace(",", ""):
            missing_numbers.append(token)

    missing_names = []
    for name in names:
        norm, _ = _normalize_with_map(name)
        parts = [p for p in norm.split() if len(p) > 1]
        if not parts or not all(p in source_norm for p in parts):
            missing_names.append(name)

    return {
        "numbers_in_draft": len(numbers),
        "numbers_not_in_source": sorted(set(missing_numbers)),
        "names_in_draft": len(names),
        "names_not_in_source": sorted(set(missing_names)),
        "handling": (
            "Each item listed is a claim without a locator in the material you supplied. Add the source "
            "locator, narrow the claim, or mark it UNCHECKED before release."
        ),
        "disclaimer": (
            "Presence in the supplied notes is not support, and absence is not falsity: the number may come "
            "from a document you did not paste. This is a locating aid, not verification."
        ),
    }


def diff_meaning(original: str, edited: str) -> dict[str, Any]:
    """Compare an untouched draft with an edited draft for lost substance."""
    if not original.strip() or not edited.strip():
        raise ValueError("original and edited must both be non-empty")

    orig_norm, _ = _normalize_with_map(original)
    edit_norm, _ = _normalize_with_map(edited)

    lost_numbers = [n for n in _extract_numbers(original) if n.lower().replace(",", "") not in edit_norm.replace(",", "")]
    added_numbers = [n for n in _extract_numbers(edited) if n.lower().replace(",", "") not in orig_norm.replace(",", "")]

    lost_names = [n for n in _extract_names(original) if _normalize_with_map(n)[0] not in edit_norm]
    added_names = [n for n in _extract_names(edited) if _normalize_with_map(n)[0] not in orig_norm]

    orig_quotes = [re.sub(r"\s+", " ", (m.group(1) or m.group(2) or "")).strip() for m in _QUOTE_RE.finditer(original)]
    lost_quotes = []
    for q in orig_quotes:
        if len(_words(q)) < 2:
            continue
        qn, _ = _normalize_with_map(q)
        if qn not in edit_norm:
            lost_quotes.append(q)

    def qualifier_rate(text: str) -> float:
        wc = max(1, len(_words(text)))
        total = len(_QUALIFIER_RE.findall(text))
        return round(total * 1000.0 / wc, 1)

    orig_q = qualifier_rate(original)
    edit_q = qualifier_rate(edited)
    qualifier_delta = round(edit_q - orig_q, 1)

    risks: list[str] = []
    level = "low"
    if lost_numbers or lost_names or lost_quotes:
        level = "high"
        if lost_numbers:
            risks.append(f"{len(lost_numbers)} number(s) removed: {', '.join(lost_numbers[:6])}")
        if lost_names:
            risks.append(f"{len(lost_names)} name(s) removed: {', '.join(lost_names[:6])}")
        if lost_quotes:
            risks.append(f"{len(lost_quotes)} direct quotation(s) no longer appear verbatim")
    elif qualifier_delta <= -max(3.0, orig_q * 0.35):
        level = "medium"
        risks.append(
            f"Qualifier density fell from {orig_q} to {edit_q} per 1,000 words; check that uncertainty was not strengthened."
        )

    if added_numbers:
        risks.append(f"{len(added_numbers)} number(s) appear only in the edited copy: {', '.join(added_numbers[:6])}")
    if added_names:
        risks.append(f"{len(added_names)} name(s) appear only in the edited copy: {', '.join(added_names[:6])}")

    return {
        "risk": level,
        "lost_numbers": sorted(set(lost_numbers)),
        "added_numbers": sorted(set(added_numbers)),
        "lost_names": sorted(set(lost_names)),
        "added_names": sorted(set(added_names)),
        "lost_quotes": lost_quotes,
        "qualifier_density": {"original": orig_q, "edited": edit_q, "delta": qualifier_delta},
        "notes": risks or ["No lost numbers, names, or quotations detected by this check."],
        "disclaimer": (
            "Catches substance that disappeared, not meaning that shifted while keeping the same words. "
            "Read both passages for scope and causal language."
        ),
    }
