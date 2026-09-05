**English** · [Português](post.pt-BR.md)

# Short post (feed / reels), pointing to the article and the repository

> **Publishing note, not part of the post.** Introduction for the feed or a reels caption,
> with a budget of up to 3,000 characters. The full text is in
> [artigo.en.md](artigo.en.md); measurements come from the
> [release document](../2026-09-04-release.en.md).
> Replace the link placeholder after publishing the article. The body is plain text and
> does not rely on Markdown formatting. Figures are in [figuras/en/](figuras/en/).

---

A customer list can repeat the same city hundreds of times.
Could it take up less space without hiding that structure?

That is the idea behind TCF, Tabular Compact Format: represent repetitive data compactly
and losslessly while keeping text that can be opened in an editor.

For example, three consecutive occurrences of a city can be written as *3|Sao Paulo.
The marker means "repeat this value three times." The information remains; only its
representation changes.

In the four-person example in the article, the same data takes 451 bytes in compact JSON,
277 in CSV and 242 in TCF, with exact reconstruction verified. These sizes are without an
external compressor and apply to that example, not to every table.

The point goes beyond size. Because the marker also carries a count, some queries can use
the structure without reconstructing every record. With the view() function, a sum filtered
by city can access just the city and amount columns without decoding the others.

This does not make TCF a replacement for gzip: the two can be combined. In the example,
JSON and TCF tie in size under gzip, while compressed CSV is smaller. Encoding also has
a cost that needs measuring, especially when the data changes with every request.

The project is open source, still pre-1.0, and requires Python 3.10 or newer with no runtime
dependencies. It is available under the MIT license.

In the article, I explain how it works, present the measurements and discuss the limits:
[article link, fill in after publishing]

Code, documentation and examples:
https://github.com/LeoPR/TCF

#Python #Compression #DataEngineering #OpenSource #DataFormats
