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
            window.location.href = "/dashboard"
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
        url: "https://rbt.americanbehavioralsolutions.com/user/login", // Change to your domain with https
        type: "POST",
        data: data,
        dataType: "json",
        success: function(resp){
            console.log(resp);
            $error.text("").addClass("error--hidden"); // Changed " " to "" for clarity
            window.location.href = "https://rbt.americanbehavioralsolutions.com/dashboard" // Change to your domain with https
        },
        error:function(resp){
            console.log(resp);
            if(resp.responseJSON && resp.responseJSON.error) {
                console.log(resp.responseJSON.error);
                $error.text(resp.responseJSON.error).removeClass("error--hidden");
            } else {
                console.log("An unknown error occurred.");
                $error.text("An unknown error occurred.").removeClass("error--hidden");
            }
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

$(function () {
    var bindDatePicker = function() {
         $(".date").datetimepicker({
            format:'MM-DD-YYYY H:m',
             icons: {
                 time: "fa fa-clock-o",
                 date: "fa fa-calendar",
                 up: "fa fa-arrow-up",
                 down: "fa fa-arrow-down"
             }
         }).find('input:first').on("blur",function () {
             // check if the date is correct. We can accept dd-mm-yyyy and yyyy-mm-dd.
             // update the format if it's yyyy-mm-dd
             var date = parseDate($(this).val());
 
             if (! isValidDate(date)) {
                 //create date based on momentjs (we have that)
                 date = moment().format('YYYY-MM-DD');
             }
 
             $(this).val(date);
         });
     }
    
    var isValidDate = function(value, format) {
         format = format || false;
         // lets parse the date to the best of our knowledge
         if (format) {
             value = parseDate(value);
         }
 
         var timestamp = Date.parse(value);
 
         return isNaN(timestamp) == false;
    }
    
    var parseDate = function(value) {
         var m = value.match(/^(\d{1,2})(\/|-)?(\d{1,2})(\/|-)?(\d{4})$/);
         if (m)
             value = m[5] + '-' + ("00" + m[3]).slice(-2) + '-' + ("00" + m[1]).slice(-2);
 
         return value;
    }
    
    bindDatePicker();
  });