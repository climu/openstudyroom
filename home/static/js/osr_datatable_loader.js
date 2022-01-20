"use strict";
(function(osr_datatable_loader){
  // init function
  osr_datatable_loader.init = ({id, url, columns}) => {
    // create the datatable
    $(`#${id}`).DataTable({
      ajax: {
        url: url,
        dataSrc: 'data'
      },
      columns: columns.map(({key}) => { return {data: key}})
    });
    // load the data
  }


})(window.osr_datatable_loader = window.osr_datatable_loader || {})