
var newTsumego = function(){
  $.ajax({
      type:"GET",
      url:"/wgo/tsumego-api/",
      error:function(){
        alert("Something went wrong.")
      },
      success: function(result){
        showTsumego(result)
      }
  });
  }

var showTsumego = function(sgf){
  element = document.getElementById("tsumego-player")
  var coords=sgf.match(/\[..\]/g);
  var xList = [];
  var yList = [];
  coords.forEach(c=> {
    xList.push(c[1].charCodeAt(0) - 97)
    yList.push(c[2].charCodeAt(0) - 97)
  })

  var top = Math.max(0, Math.min(...yList)-1)
  var left = Math.max(0, Math.min(...xList)-1)
  var right = Math.max(0, 17- Math.max(...xList))
  var bottom = Math.max(0, 17- Math.max(...yList))

  // if one var is 1 we change it to 0 to see the edge of the board
  if (top == 1) {top = 0}
  if (left == 1) {left = 0}
  if (right == 1) {right = 0}
  if (bottom == 1) {bottom = 0}

  // we need to make sure width is smaller than height otherwise wgo width overflow on calendar
  // exemple to reproduce "(;AB[cr][dq][ep][eq][fp][hp][iq][jq]AW[bq][br][co][cq][dp][en][fo][fq][ho][io][ko][kp][kr][lq]C[problem 99])"
  while (Math.abs(19 - top - bottom) < Math.abs(19- left -right)){
    // we add some extra lines to top/bottom: decrese top/bottom vars
    if (top > 1) {top -= 1}
    if (bottom > 1) {bottom -= 1}
  }

  var player = new WGo.BasicPlayer(element, {
    sgf: sgf,
    layout: "left: [], bottom: [], right: [], top: []",
    board:{
      section: {
        top: top,
        left: left,
        right: right,
        bottom: bottom
      },
    }
  });

  player.board.addEventListener("click", function(x, y, event){
          newTsumego()
        })

}


newTsumego()
