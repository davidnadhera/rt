function showDetail(id, hrana, koef = '0.0') {
  if (document.getElementById("detail"+id).innerHTML === "") {  
      if ((id === "") || (hrana === "") || (koef === "")) {
        document.getElementById("detail"+id).innerHTML = "";
        return;
      } else {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onreadystatechange = function() {
          if (this.readyState == 4 && this.status == 200) {
            document.getElementById("detail"+id).innerHTML = this.responseText;
          }
        };
        xmlhttp.open("GET","../ajax/detail/"+hrana+"/"+koef,true);
        xmlhttp.send();
      }
  } else {
      document.getElementById("detail"+id).innerHTML = "";
      document.getElementById("btn"+id).blur();
  }    
}


function showRoute(id) {
  if (document.getElementById("route"+id).innerHTML === "") {  
      if (id === "") {
        document.getElementById("route"+id).innerHTML = "";
        return;
      } else {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onreadystatechange = function() {
          if (this.readyState == 4 && this.status == 200) {
            document.getElementById("route"+id).innerHTML = this.responseText;
          }
        };
        xmlhttp.open("GET", "../ajax/detail_trasy/" + id, true);
        xmlhttp.send();
      }
  } else {
      document.getElementById("route"+id).innerHTML = "";
      document.getElementById("btn"+id).blur();
  }    
}


        function getDocHeight() {
            var D = document;
            return Math.max(
            D.body.scrollHeight, D.documentElement.scrollHeight,
            D.body.offsetHeight, D.documentElement.offsetHeight,
            D.body.clientHeight, D.documentElement.clientHeight
            );
        }
        
        function isMobile() {
            try{ document.createEvent("TouchEvent"); return true; }
            catch(e){ return false; }
        }


