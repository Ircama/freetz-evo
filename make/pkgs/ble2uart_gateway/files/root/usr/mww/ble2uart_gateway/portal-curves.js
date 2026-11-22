/*! d3-shape 3.2.0
Copyright 2010-2022 Mike Bostock

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.
*/
var PortalCurves=(()=>{var l=Object.defineProperty;var _=Object.getOwnPropertyDescriptor;var h=Object.getOwnPropertyNames;var b=Object.prototype.hasOwnProperty;var y=(e,t)=>{for(var o in t)l(e,o,{get:t[o],enumerable:!0})},v=(e,t,o,a)=>{if(t&&typeof t=="object"||typeof t=="function")for(let r of h(t))!b.call(e,r)&&r!==o&&l(e,r,{get:()=>t[r],enumerable:!(a=_(t,r))||a.enumerable});return e};var k=e=>v(l({},"__esModule",{value:!0}),e);var O={};y(O,{curveMonotoneX:()=>p});function m(e){return e<0?-1:1}function c(e,t,o){var a=e._x1-e._x0,r=t-e._x1,s=(e._y1-e._y0)/(a||r<0&&-0),i=(o-e._y1)/(r||a<0&&-0),f=(s*r+i*a)/(a+r);return(m(s)+m(i))*Math.min(Math.abs(s),Math.abs(i),.5*Math.abs(f))||0}function d(e,t){var o=e._x1-e._x0;return o?(3*(e._y1-e._y0)/o-t)/2:t}function u(e,t,o){var a=e._x0,r=e._y0,s=e._x1,i=e._y1,f=(s-a)/3;e._context.bezierCurveTo(a+f,r+f*t,s-f,i-f*o,s,i)}function n(e){this._context=e}n.prototype={areaStart:function(){this._line=0},areaEnd:function(){this._line=NaN},lineStart:function(){this._x0=this._x1=this._y0=this._y1=this._t0=NaN,this._point=0},lineEnd:function(){switch(this._point){case 2:this._context.lineTo(this._x1,this._y1);break;case 3:u(this,this._t0,d(this,this._t0));break}(this._line||this._line!==0&&this._point===1)&&this._context.closePath(),this._line=1-this._line},point:function(e,t){var o=NaN;if(e=+e,t=+t,!(e===this._x1&&t===this._y1)){switch(this._point){case 0:this._point=1,this._line?this._context.lineTo(e,t):this._context.moveTo(e,t);break;case 1:this._point=2;break;case 2:this._point=3,u(this,d(this,o=c(this,e,t)),o);break;default:u(this,this._t0,o=c(this,e,t));break}this._x0=this._x1,this._x1=e,this._y0=this._y1,this._y1=t,this._t0=o}}};function C(e){this._context=new x(e)}(C.prototype=Object.create(n.prototype)).point=function(e,t){n.prototype.point.call(this,t,e)};function x(e){this._context=e}x.prototype={moveTo:function(e,t){this._context.moveTo(t,e)},closePath:function(){this._context.closePath()},lineTo:function(e,t){this._context.lineTo(t,e)},bezierCurveTo:function(e,t,o,a,r,s){this._context.bezierCurveTo(t,e,a,o,s,r)}};function p(e){return new n(e)}return k(O);})();
