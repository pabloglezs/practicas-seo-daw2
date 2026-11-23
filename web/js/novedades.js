var novedades = [
  {n: "Camiseta vintage", u: "/productos/camisetas/camiseta-vintage.html"},
  {n: "Pantalón cargo", u: "/productos/pantalones/pantalon-cargo.html"}
];
var ul = document.getElementById("lista");
novedades.forEach(function (p) {
  var li = document.createElement("li");
  var a = document.createElement("a");
  a.href = p.u; a.textContent = p.n;
  li.appendChild(a); ul.appendChild(li);
});
