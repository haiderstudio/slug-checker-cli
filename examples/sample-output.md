--- check the good slugs ---
OK — 5 slug(s) checked, all slugs are clean.
--- check the bad slugs ---
FAIL examples/bad-slugs.txt:1: 'My First Post': uppercase letter 'M'
FAIL examples/bad-slugs.txt:1: 'My First Post': space in slug
FAIL examples/bad-slugs.txt:2: 'my_first_post': underscore in slug
FAIL examples/bad-slugs.txt:3: '-leading-hyphen': starts with a hyphen
FAIL examples/bad-slugs.txt:4: 'trailing-hyphen-': ends with a hyphen
FAIL examples/bad-slugs.txt:5: 'double--hyphen': double hyphen '--'
FAIL examples/bad-slugs.txt:6: 'café-guide': bad character 'é'
FAIL examples/bad-slugs.txt:7: 'my/post': bad character '/'
FAIL examples/bad-slugs.txt:8: 'UPPERCASE': uppercase letter 'U'
Checked 8 slug(s), 9 problem(s) in 8 slug(s).
--- check the posts ---
FAIL examples/posts/bad-post.md:3: 'My First Post': uppercase letter 'M'
FAIL examples/posts/bad-post.md:3: 'My First Post': space in slug
Checked 2 slug(s), 2 problem(s) in 1 slug(s).
