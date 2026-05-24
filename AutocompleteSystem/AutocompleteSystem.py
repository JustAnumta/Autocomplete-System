import tkinter as tk


# data structure for radix tree

class RadixNode:
    def __init__(self):
        self.children = {}   # stores edges and next nodes
        self.end      = False
        self.count    = 0    # how many times selected


class RadixTree:

    def __init__(self):
        self.root = RadixNode()

    # insert a word or phrase into the tree
    def insert(self, word):
        node = self.root
        while True:
            for edge in list(node.children.keys()):
                i = 0

                # find common prefix between edge and word
                while i < len(edge) and i < len(word) and edge[i] == word[i]:
                    i += 1

                if i == 0:
                    continue

                # full match of edge, go deeper
                if i == len(edge):
                    node = node.children[edge]
                    word = word[i:]
                    break

                # split edge if partial match
                existing_child = node.children[edge]
                new_node = RadixNode()
                new_node.children[edge[i:]] = existing_child

                node.children[edge[:i]] = new_node
                del node.children[edge]

                # mark end if word finishes here
                if i == len(word):
                    new_node.end = True
                else:
                    leaf = RadixNode()
                    leaf.end = True
                    new_node.children[word[i:]] = leaf

                return

            else:
                # no match, just add new edge
                leaf = RadixNode()
                leaf.end = True
                node.children[word] = leaf
                return

            if word == "":
                node.end = True
                return

    # increase frequency when user selects a word
    def increment(self, word):
        node = self.root
        remaining = word

        while remaining:
            matched = False
            for edge in node.children:
                if remaining.startswith(edge):
                    node = node.children[edge]
                    remaining = remaining[len(edge):]
                    matched = True
                    break
            if not matched:
                return

        if node.end:
            node.count += 1

    # move to node that matches given prefix
    def findnode(self, prefix):
        node = self.root

        while prefix:
            for edge in node.children:
                if prefix.startswith(edge):
                    node = node.children[edge]
                    prefix = prefix[len(edge):]
                    break

                # handle case where prefix ends inside edge
                elif edge.startswith(prefix):
                    bridge = RadixNode()
                    bridge.children[edge[len(prefix):]] = node.children[edge]
                    return bridge
            else:
                return None

        return node

    # collect all words from a node
    def collectwords(self, node, prefix, results):
        if node.end:
            results.append((prefix, node.count))

        for edge, child in node.children.items():
            self.collectwords(child, prefix + edge, results)

    # fuzzy search using edit distance
    def fuzzy_search(self, word, max_distance=2):
        results = []
        initial_row = list(range(len(word) + 1))

        for edge, child in self.root.children.items():
            self._fuzzy_recurse(child, edge, edge, word,
                                initial_row, results, max_distance)

        # sort by distance then frequency
        results.sort(key=lambda x: (x[1], -x[2], x[0]))
        return results

    # recursive helper for fuzzy search
    def _fuzzy_recurse(self, node, edge_label, full_prefix,
                       word, prev_row, results, max_distance):

        row = prev_row

        for ch in edge_label:
            current_row = [row[0] + 1]

            for j, target_ch in enumerate(word):
                current_row.append(min(
                    current_row[j] + 1,
                    row[j + 1] + 1,
                    row[j] + (0 if ch == target_ch else 1),
                ))

            row = current_row

            # stop early if distance too large
            if min(row) > max_distance:
                return

        # add result if valid match
        if node.end and row[-1] <= max_distance:
            results.append((full_prefix, row[-1], node.count))

        # continue deeper
        for edge, child in node.children.items():
            self._fuzzy_recurse(child, edge, full_prefix + edge,
                                word, row, results, max_distance)


# build tree

tree = RadixTree()

# load single words
with open("Words.txt", "r") as f:
    for line in f:
        w = line.strip().lower()
        if w.isalpha() and len(w) >= 3:
            tree.insert(w)

# load phrases if file exists
try:
    with open("Phrases.txt", "r") as f:
        for line in f:
            phrase = line.strip().lower()
            if len(phrase) >= 3:
                tree.insert(phrase)
except FileNotFoundError:
    pass


# recent history settings

RECENT_CAP = 10
RECENCY_BOOST = 50
recent = []

RECENT_PREFIX = "🕐 "


# boost score for recent selections
def get_boost(word):
    if word in recent:
        pos = recent.index(word)
        return RECENCY_BOOST * (RECENT_CAP - pos)
    return 0


# update recent list
def push_recent(word):
    if word in recent:
        recent.remove(word)

    recent.insert(0, word)

    if len(recent) > RECENT_CAP:
        recent.pop()


# prefix analytics

TRENDING_SHOW = 3
prefix_counts = {}
total_queries = 0
total_length = 0


# track what user types
def record_prefix(prefix):
    global total_queries, total_length

    prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
    total_queries += 1
    total_length += len(prefix)


# get top searched prefixes
def get_trending(n=TRENDING_SHOW):
    if not prefix_counts:
        return []

    return sorted(prefix_counts, key=lambda p: -prefix_counts[p])[:n]


# average query length
def avg_query_length():
    if total_queries == 0:
        return 0.0

    return round(total_length / total_queries, 1)


# update stats display
def update_stats_bar():
    trending = get_trending()

    trend_str = "📈  " + ",  ".join(trending) if trending else "📈  —"
    avg_str = f"   ·   ⌀ {avg_query_length()} chars"

    stats_label.config(text=trend_str + avg_str)


# update suggestions on typing
def update_suggestions(event=None):
    raw = entry.get().lower()
    listbox.delete(0, tk.END)

    # show recent if empty
    if not raw.strip():
        for word in recent:
            listbox.insert(tk.END, RECENT_PREFIX + word)

        update_stats_bar()
        return

    # split into context and last word
    last_space = raw.rfind(" ")

    if last_space == -1:
        context = ""
        last_token = raw
    else:
        context = raw[:last_space + 1]
        last_token = raw[last_space + 1:]

    record_prefix(last_token if last_token else raw.strip())
    update_stats_bar()

    seen = set()
    phrases = []

    # fuzzy mode
    if fuzzy_var.get():
        target = last_token if last_token else raw.strip()

        raw_results = tree.fuzzy_search(target, max_distance=2)

        raw_results.sort(
            key=lambda x: (x[1], -(x[2] + get_boost(context + x[0])), x[0])
        )

        for word, _dist, _count in raw_results[:100]:
            phrase = context + word

            if phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)

    # prefix mode
    else:
        # full phrase search
        if context:
            phrase_node = tree.findnode(raw)

            if phrase_node:
                full_matches = []
                tree.collectwords(phrase_node, raw, full_matches)

                full_matches.sort(
                    key=lambda x: (-(x[1] + get_boost(x[0])), x[0])
                )

                for phrase, _count in full_matches:
                    if phrase not in seen:
                        seen.add(phrase)
                        phrases.append(phrase)

        # last word search
        if last_token:
            token_node = tree.findnode(last_token)

            if token_node:
                token_matches = []
                tree.collectwords(token_node, last_token, token_matches)

                token_matches.sort(
                    key=lambda x: (-(x[1] + get_boost(context + x[0])), x[0])
                )

                for word, _count in token_matches:
                    phrase = context + word

                    if phrase not in seen:
                        seen.add(phrase)
                        phrases.append(phrase)

    for phrase in phrases[:100]:
        listbox.insert(tk.END, phrase)


# fill entry when user clicks suggestion
def fill_word(event):
    if not listbox.curselection():
        return

    selected = listbox.get(listbox.curselection())

    if selected.startswith(RECENT_PREFIX):
        selected = selected[len(RECENT_PREFIX):]

    entry.delete(0, tk.END)
    entry.insert(0, selected)

    # only increment last word
    last_word = selected.strip().rsplit(" ", 1)[-1]
    tree.increment(last_word)

    push_recent(selected)
    update_suggestions()


# ui setup

root = tk.Tk()
root.title("Autocomplete System")
root.geometry("400x500")

tk.Label(root, text="Type a word", font=("Cambria", 12)).pack(pady=(10, 0))

entry = tk.Entry(root, font=("Cambria", 14))
entry.pack(pady=10, padx=10, fill=tk.X)
entry.bind("<KeyRelease>", update_suggestions)

fuzzy_var = tk.BooleanVar(value=False)

tk.Checkbutton(
    root,
    text="Fuzzy Search (Typo Tolerance)",
    variable=fuzzy_var,
    font=("Cambria", 10),
    command=update_suggestions,
).pack()

listbox = tk.Listbox(root, font=("Cambria", 12))
listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
listbox.bind("<<ListboxSelect>>", fill_word)

stats_label = tk.Label(
    root,
    text="📈 Trending: —   |   ⌀ Avg length: 0.0",
    font=("Cambria", 9),
    fg="#555555",
    anchor="w",
)
stats_label.pack(fill=tk.X, padx=12, pady=(0, 8))

root.mainloop()