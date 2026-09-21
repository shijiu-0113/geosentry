---
title: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta
url: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta
source: developer.mozilla.org
crawled: 2026-09-19 00:40:52
---

---
title: "<meta> HTML metadata element"
url: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta
hostname: mozilla.org
description: The HTML element represents metadata that cannot be represented by other meta-related elements, such as , , , , or .
sitename: developer.mozilla.org
date: "2026-04-24"
---
# `<meta>` HTML metadata element

            ## 
        
        
          Baseline
        
        Widely available
        *
        
                
                      
                    
                      
                    
                      
                    
              
        
      

      This feature is well established and works across many devices and browser versions. It’s been available across browsers since July 2015.

* Some parts of this feature may have varying levels of support.

The **`<meta>`** HTML element represents metadata that cannot be represented by other meta-related elements, such as `<base>`, `<link>`, `<script>`, `<style>`, or `<title>`.

The type of metadata provided by the `<meta>` element can be one of the following:

- If the `name` attribute is set, the`<meta>` element provides*document-level metadata* that applies to the whole page.
- If the `http-equiv` attribute is set, the`<meta>` element acts as a*pragma directive* to simulate directives that could otherwise be given by an HTTP header.
- If the `charset` attribute is set, the`<meta>` element is a*charset declaration* , giving the character encoding in which the document is encoded.
- If the `itemprop` attribute is set, the`<meta>` element provides*user-defined metadata* .

## Attributes

This element includes the global attributes.

**Note:**
The `name` attribute has a specific meaning for the `<meta>` element.
The `itemprop` attribute must not be set on a `<meta>` element that includes a `name`, `http-equiv`, or `charset` attribute.

- `charset`
- 
This attribute declares the document's character encoding. If the attribute is present, its value must be an ASCII case-insensitive match for the string `"utf-8"` , because UTF-8 is the only valid encoding for HTML5 documents.`<meta>` elements which declare a character encoding must be located entirely within the first 1024 bytes of the document.
- `content`
- 
This attribute contains the value for the `http-equiv` or`name` attribute, depending on which is used.
- `http-equiv`
- 
Defines a pragma directive, which are instructions for the browser for processing the document. The attribute's name is short for `http-equivalent` because the allowed values are names of equivalent HTTP headers.
- `media`
- 
The `media` attribute defines which media the theme color defined in the`content` attribute should be applied to.
Its value is a media query, which defaults to`all` if the attribute is missing.
This attribute is only relevant when the element's`name` attribute is set to`theme-color` .
Otherwise, it has no effect, and should not be included.
- `name`
- 
The `name` and`content` attributes can be used together to provide document metadata in terms of name-value pairs, with the`name` attribute giving the metadata name, and the`content` attribute giving the value.

## Examples

### Setting a meta description

The following `<meta>` tag provides a `description` as metadata for the web page:

```
<meta
  name="description"
  content="The HTML reference describes all elements and attributes of HTML, including global attributes that apply to all elements." />
```
### Setting a page redirect

The following example uses `http-equiv="refresh"` to direct the browser to perform a redirect.
The `content="3;url=https://www.mozilla.org"` attribute will redirect page to `https://www.mozilla.org` after 3 seconds:

```
<meta http-equiv="refresh" content="3;url=https://www.mozilla.org" />
```
## Technical summary

| Content categories | Metadata content. If the `itemprop` attribute is present:         flow content,         phrasing content. | 
|---|---|
| Permitted content | None; it is a void element. | 
| Tag omission | Must have a start tag and must not have an end tag. | 
| Permitted parents |  | 
| Implicit ARIA role | No corresponding role | 
| Permitted ARIA roles | No `role` permitted | 
| DOM interface | `HTMLMetaElement` | 

## Specifications

| Specification | 
|---|
| HTML # the-meta-element |