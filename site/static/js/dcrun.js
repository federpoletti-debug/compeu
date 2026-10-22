/* CompEU page runtime.
 *
 * The pages are designed in Claude Design as .dc.html artboards. The site build
 * (src/compeu/dc.py) turns each artboard into a JSON template and a logic script;
 * this file renders them in the browser with Preact (vendor/preact.min.js).
 *
 * Template nodes are ["tag", {attrs}, [children]] or text. Supported:
 *   {{a.b}} holes in text and attributes (a whole-value hole keeps the raw value:
 *   a function for onClick or ref, a boolean for disabled),
 *   <sc-for list as> and <sc-if value> blocks, and the logic class
 *   `class Component extends DCLogic` with renderVals(), state and React lifecycle.
 * Links between artboards ("Why.dc.html#x"), written in the markup or computed by
 * the logic, are sent to the matching page of the site.
 */
(function () {
  'use strict';
  var P = window.preact;
  var h = P.h, Fragment = P.Fragment;
  var HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
  var FULL = /^\{\{\s*([^}]+?)\s*\}\}$/;
  var ARTBOARD = /^([A-Za-z0-9_-]+\.dc\.html)(#.*)?$/;
  var links = {};

  function lookup(scope, path) {
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (path === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(path)) return Number(path);
    var parts = path.split('.'), v = scope;
    for (var i = 0; i < parts.length; i++) {
      if (v == null) return undefined;
      v = v[parts[i]];
    }
    return v;
  }

  function value(raw, scope) {
    if (raw.indexOf('{{') < 0) return raw;
    var m = FULL.exec(raw);
    if (m) return lookup(scope, m[1]);
    return raw.replace(HOLE, function (_, p) {
      var v = lookup(scope, p);
      return v == null ? '' : String(v);
    });
  }

  function text(raw, scope) {
    var v = value(raw, scope);
    return v == null || v === false || typeof v === 'object' || typeof v === 'function' ? '' : String(v);
  }

  function children(kids, scope) {
    var out = [];
    for (var i = 0; i < kids.length; i++) out.push(node(kids[i], scope));
    return out;
  }

  function node(n, scope) {
    if (typeof n === 'string') return text(n, scope);
    var tag = n[0], attrs = n[1], kids = n[2];
    if (tag === 'sc-for') {
      var list = value(attrs.list || '', scope) || [];
      var as = attrs.as || 'item';
      return list.map(function (item, i) {
        var s = Object.create(scope);
        s[as] = item;
        s.$index = i;
        return h(Fragment, { key: item && item.key != null ? item.key : i }, children(kids, s));
      });
    }
    if (tag === 'sc-if') return value(attrs.value || '', scope) ? children(kids, scope) : null;
    var props = {};
    for (var name in attrs) {
      if (name.indexOf('hint-') === 0) continue;
      var v = value(attrs[name], scope);
      if (name === 'href' && typeof v === 'string') {
        var m = ARTBOARD.exec(v);
        if (m && links[m[1]] != null) v = links[m[1]] + (m[2] || '');
      }
      props[name] = v;
    }
    return h(tag, props, children(kids, scope));
  }

  function DCLogicFor(template) {
    function DCLogic(props) {
      P.Component.call(this, props);
    }
    DCLogic.prototype = Object.create(P.Component.prototype);
    DCLogic.prototype.constructor = DCLogic;
    DCLogic.prototype.render = function () {
      return node(template, this.renderVals());
    };
    return DCLogic;
  }

  function mount(container, templateScript, makeLogic, pages) {
    links = pages || {};
    var tpl = JSON.parse(templateScript.textContent);
    var root = tpl.length === 1 ? tpl[0] : ['div', {}, tpl];
    var DCLogic = DCLogicFor(root);
    var Component = makeLogic(DCLogic, DCLogic, null);
    P.render(h(Component, {}), container);
  }

  window.dcrun = { mount: mount, lookup: lookup, value: value };
})();
