---
layout: default
---

# Welcome to the Blog

Here are the latest articles:

<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
      <br>
      <small>{{ post.date | date: "%B %d, %Y" }}</small>
    </li>
  {% endfor %}
</ul>
