# Specification — normalize_tags

`normalize_tags(tags: list[str]) -> list[str]`

Given a list of raw tag strings, return the normalized tag list produced by
applying exactly these steps in order:

1. Strip leading and trailing whitespace from each tag.
2. Convert each tag to lowercase.
3. Drop tags that are empty after step 1.
4. Remove duplicates, keeping the **first** occurrence of each tag.
5. Return the tags in the **order produced by steps 1–4**. The
   specification mandates no reordering of any kind.
