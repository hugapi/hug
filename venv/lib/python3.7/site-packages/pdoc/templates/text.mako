## Define mini-templates for each portion of the doco.

<%!
  def indent(s, spaces=4):
      new = s.replace('\n', '\n' + ' ' * spaces)
      return ' ' * spaces + new.strip()
%>

<%def name="deflist(s)">:${indent(s)[1:]}</%def>

<%def name="h3(s)">### ${s}
</%def>

<%def name="function(func)" buffered="True">
    <%
        returns = show_type_annotations and f.return_annotation() or ''
        if returns:
            returns = ' -> ' + returns
    %>
`${func.name}(${", ".join(func.params(annotate=show_type_annotations))})${returns}`
${func.docstring | deflist}
</%def>

<%def name="variable(var)" buffered="True">
`${var.name}`
${var.docstring | deflist}
</%def>

<%def name="class_(cls)" buffered="True">
`${cls.name}(${", ".join(cls.params(annotate=show_type_annotations))})`
${cls.docstring | deflist}
<%
  class_vars = cls.class_variables(show_inherited_members, sort=sort_identifiers)
  static_methods = cls.functions(show_inherited_members, sort=sort_identifiers)
  inst_vars = cls.instance_variables(show_inherited_members, sort=sort_identifiers)
  methods = cls.methods(show_inherited_members, sort=sort_identifiers)
  mro = cls.mro()
  subclasses = cls.subclasses()
%>
% if mro:
    ${h3('Ancestors (in MRO)')}
    % for c in mro:
    * ${c.refname}
    % endfor

% endif
% if subclasses:
    ${h3('Descendants')}
    % for c in subclasses:
    * ${c.refname}
    % endfor

% endif
% if class_vars:
    ${h3('Class variables')}
    % for v in class_vars:
${variable(v) | indent}

    % endfor
% endif
% if static_methods:
    ${h3('Static methods')}
    % for f in static_methods:
${function(f) | indent}

    % endfor
% endif
% if inst_vars:
    ${h3('Instance variables')}
    % for v in inst_vars:
${variable(v) | indent}

    % endfor
% endif
% if methods:
    ${h3('Methods')}
    % for m in methods:
${function(m) | indent}

    % endfor
% endif
</%def>

## Start the output logic for an entire module.

<%
  variables = module.variables()
  classes = module.classes()
  functions = module.functions()
  submodules = module.submodules()
  heading = 'Namespace' if module.is_namespace else 'Module'
%>

${heading} ${module.name}
=${'=' * (len(module.name) + len(heading))}
${module.docstring}


% if submodules:
Sub-modules
-----------
    % for m in submodules:
* ${m.name}
    % endfor
% endif

% if variables:
Variables
---------
    % for v in variables:
${variable(v)}

    % endfor
% endif

% if functions:
Functions
---------
    % for f in functions:
${function(f)}

    % endfor
% endif

% if classes:
Classes
-------
    % for c in classes:
${class_(c)}

    % endfor
% endif
