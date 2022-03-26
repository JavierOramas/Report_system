$("form[name=signup_form]").submit(function(e){

    var $form =  $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
        url: "/user/signup",
        type: "POST",
        data: data,
        dataType: "json",
        success: function(resp){
            console.log(resp);
            $error.text(" ").addClass("error--hidden");
            window.location.href = "/dashboard/"
        },
        error:function(resp){
            console.log(resp);
            console.log(resp.responseJSON.error)
            $error.text(resp.responseJSON.error).removeClass("error--hidden");
        },
    });
    e.preventDefault();
});

$("form[name=login_form]").submit(function(e){

    var $form =  $(this);
    var $error = $form.find(".error");
    var data = $form.serialize();

    $.ajax({
        url: "/user/login",
        type: "POST",
        data: data,
        dataType: "json",
        success: function(resp){
            console.log(resp);
            $error.text(" ").addClass("error--hidden");
            window.location.href = "/dashboard/"
        },
        error:function(resp){
            console.log(resp);
            console.log(resp.responseJSON.error)
            $error.text(resp.responseJSON.error).removeClass("error--hidden");
        },
    });
    e.preventDefault();
});

// $("form[name=edit_form]").submit(function(e){

//     var $form =  $(this);
//     var $error = $form.find(".error");
//     var data = $form.serialize();

//     $.ajax({
//         url: "/edit/*",
//         type: "POST",
//         data: data,
//         dataType: "json",
//         success: function(resp){
//             console.log(resp);
//             $error.text(" ").addClass("error--hidden");
//             window.location.href = "/dashboard/"
//         },
//         error:function(resp){
//             console.log(resp);
//             console.log(resp.responseJSON.error)
//             $error.text(resp.responseJSON.error).removeClass("error--hidden");
//         },
//     });
//     e.preventDefault();
// });

function filterProv() {
    // Declare variables
    var input, filter, table, tr, td, i, txtValue;
    input = document.getElementById("ProviderID");
    filter = input.value.toUpperCase();

    table = document.getElementById("entries");
    tr = table.getElementsByTagName("tr");

    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td")[2];
        if (td) {
        txtValue = td.textContent || td.innerText;
        if (filter == 'ALL' || txtValue.toUpperCase().indexOf(filter) > -1) {
          tr[i].style.display = "";
        } else {
          tr[i].style.display = "none";
        }
      }
    }
  }

  $( document ).ready(function() {
    $("#FilterDateFrom").datepicker({ 
        format: 'mm-dd-yyyy HH:MM'
    });
    $("#FilterDateFrom").on("change", function () {
        var fromdate = $(this).val();
        alert(fromdate);
    });
});

$( document ).ready(function() {
    $("#FilterDateTo").datepicker({ 
        format: 'mm-dd-yyyy HH:MM'
    });
    $("#FilterDateTo").on("change", function () {
        var fromdate = $(this).val();
        alert(fromdate);
    });
});

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})