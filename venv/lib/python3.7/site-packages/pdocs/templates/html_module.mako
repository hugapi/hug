## -*- coding: utf-8 -*-
<%!
import pygments
import pdocs.doc
import pdocs.html_helpers as hh
%>

<%inherit file="html_frame.mako"/>

<%def name="show_source(d)">
  % if show_source_code and d.source is not None and len(d.source) > 0:
  <p class="source_link"><a href="javascript:void(0);" onclick="toggle('${hh.sourceid(d)}', this);">Show source &equiv;</a></p>
  <div id="${hh.sourceid(d)}" class="source">
    ${hh.decode(hh.clean_source_lines(d.source))}
  </div>
  % endif
</%def>

<%def name="show_desc(d, limit=None)">
  <%
  inherits = (hasattr(d, 'inherits')
           and (len(d.docstring) == 0
            or d.docstring == d.inherits.docstring))
  docstring = (d.inherits.docstring if inherits else d.docstring).strip()
  if limit is not None:
    docstring = hh.glimpse(docstring, limit)
  %>
  % if len(docstring) > 0:
  % if inherits:
    <div class="desc inherited">${docstring | hh.mark}</div>
  % else:
    <div class="desc">${docstring | hh.mark}</div>
  % endif
  % endif
  % if not isinstance(d, pdocs.doc.Module):
  <div class="source_cont">${show_source(d)}</div>
  % endif
</%def>

<%def name="show_inheritance(d)">
  % if hasattr(d, 'inherits'):
    <p class="inheritance">
     <strong>Inheritance:</strong>
     % if hasattr(d.inherits, 'cls'):
       <code>${hh.link(module, d.inherits.cls.refname, link_prefix)}</code>.<code>${hh.link(module, d.inherits.refname, link_prefix)}</code>
     % else:
       <code>${hh.link(module, d.inherits.refname), link_prefix}</code>
     % endif
    </p>
  % endif
</%def>

<%def name="show_column_list(items, numcols=3)">
  <ul>
  % for item in items:
    <li class="mono">${item}</li>
  % endfor
  </ul>
</%def>

<%def name="show_module(module)">
  <%
  variables = module.variables()
  classes = module.classes()
  functions = module.functions()
  submodules = module.submodules
  %>

  <%def name="show_func(f)">
  <div class="item">
    <div class="name def" id="${f.refname}">
    <p>${f.funcdef()} ${hh.ident(f.name)}(</p><p>${f.spec() | h})</p>
    </div>
    ${show_inheritance(f)}
    ${show_desc(f)}
  </div>
  </%def>

  % if 'http_server' in context.keys() and http_server:
    <p id="nav">
      <a href="/">All packages</a>
      <% parts = module.name.split('.')[:-1] %>
      % for i, m in enumerate(parts):
        <% parent = '.'.join(parts[:i+1]) %>
        :: <a href="/${parent.replace('.', '/')}">${parent}</a>
      % endfor
    </p>
  % endif

  <header id="section-intro">
  <h1 class="title"><span class="name">${module.name}</span> module</h1>
  ${module.docstring | hh.mark}
  ${show_source(module)}
  </header>

  <section id="section-items">
    % if len(variables) > 0:
    <h2 class="section-title" id="header-variables">Module variables</h2>
    % for v in variables:
      <div class="item">
      <p id="${v.refname}" class="name">var ${hh.ident(v.name)}</p>
      ${show_desc(v)}
      </div>
    % endfor
    % endif

    % if len(functions) > 0:
    <h2 class="section-title" id="header-functions">Functions</h2>
    % for f in functions:
      ${show_func(f)}
    % endfor
    % endif

    % if len(classes) > 0:
    <h2 class="section-title" id="header-classes">Classes</h2>
    % for c in classes:
      <%
      class_vars = c.class_variables()
      smethods = c.functions()
      inst_vars = c.instance_variables()
      methods = c.methods()
      mro = c.module.mro(c)
      %>
      <div class="item">
      <p id="${c.refname}" class="name">class ${hh.ident(c.name)}</p>
      ${show_desc(c)}

      <div class="class">
        % if len(mro) > 0:
          <h3>Ancestors (in MRO)</h3>
          <ul class="class_list">
          % for cls in mro:
          <li>${hh.link(module, cls.refname, link_prefix)}</li>
          % endfor
          </ul>
        % endif
        % if len(class_vars) > 0:
          <h3>Class variables</h3>
          % for v in class_vars:
            <div class="item">
            <p id="${v.refname}" class="name">var ${hh.ident(v.name)}</p>
            ${show_inheritance(v)}
            ${show_desc(v)}
            </div>
          % endfor
        % endif
        % if len(smethods) > 0:
          <h3>Static methods</h3>
          % for f in smethods:
            ${show_func(f)}
          % endfor
        % endif
        % if len(inst_vars) > 0:
          <h3>Instance variables</h3>
          % for v in inst_vars:
            <div class="item">
            <p id="${v.refname}" class="name">var ${hh.ident(v.name)}</p>
            ${show_inheritance(v)}
            ${show_desc(v)}
            </div>
          % endfor
        % endif
        % if len(methods) > 0:
          <h3>Methods</h3>
          % for f in methods:
            ${show_func(f)}
          % endfor
        % endif
      </div>
      </div>
    % endfor
    % endif

    % if len(submodules) > 0:
    <h2 class="section-title" id="header-submodules">Sub-modules</h2>
    % for m in submodules:
      <div class="item">
      <p class="name">${hh.link(module, m.refname, link_prefix)}</p>
      ${show_desc(m, limit=300)}
      </div>
    % endfor
    % endif
  </section>
</%def>

<%def name="module_index(module)">
  <%
  variables = module.variables()
  classes = module.classes()
  functions = module.functions()
  submodules = module.submodules
  parent = module.parent
  %>
  <div id="sidebar">
    <h1>Index</h1>
    <ul id="index">
    % if parent:
    <li class="set"><h3>Super-module</h3>
      <ul>
        <li class="mono">${hh.link(module, parent.refname, link_prefix)}</li>
      </ul>
    </li>
    % endif
    % if len(variables) > 0:
    <li class="set"><h3><a href="#header-variables">Module variables</a></h3>
      ${show_column_list(map(lambda v: hh.link(module, v.refname, link_prefix), variables))}
    </li>
    % endif

    % if len(functions) > 0:
    <li class="set"><h3><a href="#header-functions">Functions</a></h3>
      ${show_column_list(map(lambda f: hh.link(module, f.refname, link_prefix), functions))}
    </li>
    % endif

    % if len(classes) > 0:
    <li class="set"><h3><a href="#header-classes">Classes</a></h3>
      <ul>
      % for c in classes:
        <li class="mono">
        <span class="class_name">${hh.link(module, c.refname, link_prefix)}</span>
        <%
          methods = c.functions() + c.methods()
        %>
        % if len(methods) > 0:
          ${show_column_list(map(lambda f: hh.link(module, f.refname, link_prefix), methods))}
        % endif
        </li>
      % endfor
      </ul>
    </li>
    % endif

    % if len(submodules) > 0:
    <li class="set"><h3><a href="#header-submodules">Sub-modules</a></h3>
      <ul>
      % for m in submodules:
        <li class="mono">${hh.link(module, m.refname, link_prefix)}</li>
      % endfor
      </ul>
    </li>
    % endif
    </ul>
  </div>
</%def>

<%block name="title">
  <title>${module.name} API documentation</title>
  <meta name="description" content="${module.docstring | hh.glimpse, trim}" />
</%block>

${module_index(module)}
<article id="content">${show_module(module)}</article>