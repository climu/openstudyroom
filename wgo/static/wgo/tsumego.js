
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

  var player = new WGo.BasicPlayer(element, {
    sgf: sgf,
    layout: "left: [], bottom: [], right: [], top: []",
    board:{
      section: {
        top: Math.max(0, Math.min(...yList)-1),
        left: Math.max(0, Math.min(...xList)-1),
        right: 17- Math.max(...xList),
        bottom: 17- Math.max(...yList)
      },
    }
  });

  player.board.addEventListener("click", function(x, y, event){
          newTsumego()
        })

}


newTsumego()
