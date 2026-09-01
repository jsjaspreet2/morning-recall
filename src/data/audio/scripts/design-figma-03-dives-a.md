---
id: design-figma-03-dives-a
title: "Figma — why not O.T., and what last-write-wins costs"
source: src/data/designs/design-figma.md §7-8
minutes: 9
---
Every collaborative editing design has one question that decides the whole thing, and it gets asked in the first five minutes. How do two people editing the same document at the same time end up seeing the same thing? This episode is about why the famous answer to that question is the wrong answer for Figma, what they use instead, and the bill that comes with it.

Two deep dives here. The first is the one everybody expects. The second is the one almost nobody reaches, and it's where a design that looked finished falls over.

So, the obvious move. Collaborative editing means Operational Transformation. Google Docs does it, it's the thing you've read about, and the instinct is to transform each incoming operation against the concurrent ones the client already applied.

Here's where that falls down. O.T. needs a transformation function for every ordered pair of operation types. Set property, create, delete, reparent, reorder, group — that's quadratic in the number of operation types, and every one of those functions is individually subtle. Figma's own engineering writeup is blunt about it. They call O.T., quote, unnecessarily complex for our problem space, end quote.

But the deeper point is the one worth carrying out of this episode. O.T. is machinery for editing a sequence, where inserting at position four changes what position seven means. Setting the fill property on an object doesn't change what any other property means. So you'd be paying for a problem the data model already designed away.

What replaces it is much smaller. Last writer wins, per property, with a single server process as the ordering authority. The server keeps the latest value any client sent for a given property on a given object. The order things arrive at that process is the order. There's nothing to transform. And notice Figma describes their system as C.R.D.T. inspired while saying plainly that it isn't using true C.R.D.Ts — because the server is central, they get to drop the vector clocks, the tombstone sets, and the merge functions a decentralized system needs to converge without a coordinator.

Three costs, and you should name all three before you're asked.

First, last write wins means somebody silently loses. Two users set the fill on the same object at the same moment. One value survives, the other disappears, with no conflict interface and no merge. That's completely acceptable for a color. It's unacceptable for a paragraph of text, which is exactly why text is the one place this model doesn't stretch.

Second, you've given up decentralization. No peer to peer, no true offline for a week and merge later, no federating between servers. Every edit to a file has to reach one process. That process is now a single point of failure, and paying for that is a whole separate dive.

Third, ordering is per file, not global. Two files are completely independent, which is fine, but any feature that spans files — a shared component library, say — can't be made atomic with an edit. Worth saying out loud before they ask.

Now the second dive, and this is the one to steer the conversation toward yourself. Sibling ordering. It looks like a detail. It is not.

The naive answer is that each object stores its index among its siblings. Either the parent holds an array of child identifiers, or each child holds an integer position.

Two distinct failures, and both are load bearing.

The first is that concurrent inserts collide. Two users each drop a layer at the same index. If the parent's list of children is modeled as one property, last writer wins means one user's entire insert vanishes — the list they didn't write is the list that survives. And if instead each child holds its own integer position, then both children claim that position and the resulting order is undefined.

The second failure is that a single drag becomes a linear write. Move one layer from the bottom of a frame holding two hundred objects up to the top, and you renumber every sibling. That's two hundred property writes, broadcast to every connected client, for one user gesture — and every single one of them is an independent last-writer-wins race.

What replaces it is fractional indexing. An object's position among its siblings is a fraction strictly between zero and one. To insert between two objects, average their indices. To insert at the very start or the very end, average with zero or with one. There's always room, because there's always a rational number between two rationals. And the payoff is the thing to say out loud: a drag now writes exactly one property, the moved object's own, and touches nothing else.

Two implementation details, because they're where this actually goes wrong in practice.

It is not a sixty-four-bit float. Repeatedly inserting at the same point halves the gap every time, and you exhaust double precision in about fifty operations. Figma stores the index as an arbitrary precision fraction encoded as a string, averages it by string manipulation, and compacts it by using the full printable A.S.C.I.I. range — base ninety-five rather than base ten.

And the parent pointer and the position are one single atomic property, not two. If they're two, a concurrent move can land the new parent and lose the new position, and the object shows up in the right frame at a meaningless place. Storing them together makes a move one indivisible write.

Three costs again.

Index strings grow. Every insertion between the same two neighbours adds roughly a character, so sustained editing in one spot produces long keys. You need a renormalization pass that rewrites a parent's children back to short, evenly spaced indices — and because that's a multi property write that must not interleave with concurrent edits, the server has to do it, never a client.

Interleaving is arbitrary. Two users inserting at the same position get a deterministic, convergent order, but not necessarily the one either of them intended. Figma's justification for accepting that is worth borrowing: a layers panel is not prose. Nobody is harmed if two simultaneously added rectangles land in the other order. That is the same trade the first dive made, one level down.

And cycles are now possible. Since parenting is just a property, two users can concurrently reparent A into B and B into A, producing a cycle that detaches an entire subtree from the document. The server rejects any parent update that would create one — the same check you'd write by walking parent pointers, enforced at the ordering authority, because that's the only place with a consistent view.

So, three things to carry out of this episode.

O.T. is machinery for editing a sequence. Figma's document is a map of objects with independent properties, so there's nothing to transform, and last writer wins with a central ordering authority is enough.

The price of that is that somebody silently loses a concurrent edit, and you accept it everywhere except text.

And sibling order is not an integer. It's a fraction between zero and one, stored as an arbitrary precision string, bundled together with the parent pointer into one atomic property — so that dragging a layer writes exactly one thing.
