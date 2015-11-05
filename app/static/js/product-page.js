//Wordcount for reviews
function countChar(val) {
    var len = val.value.length;
    if (len > 501) {
        val.value = val.value.substring(0, 500);
    } else {
        $('#charNum').text(500 - len);
    }
};

//AJAX STUFF
// wait for the DOM to be loaded 
$(document).ready(function() {
    // bind 'myForm' and provide a simple callback function 
    function passsucc(data) {
        // 'data' is the json object returned from the server 
        $(".passform button, .failform button").removeClass("process");
        $("#vinst").remove();
        $("button.vote.pass").addClass("selected").prop("disabled", true);
        $("button.vote.fail").removeClass("selected").prop("disabled", false);
        $("[rel='passtip']").tooltip('show');
        $("[rel='failtip']").tooltip('hide');
        $("#review_form").removeClass("hidden");
        $(".writerev").removeClass('hidden');
        $(".badge.points").html(data.points);
        var swidth = ((data.passes) / (data.passes + data.fails)) * 100 + "%";
        var fwidth = ((data.fails) / (data.passes + data.fails)) * 100 + "%";
        var prog = swidth / 100;
        $("div.progress-bar-success").css({
            "width": swidth
        });
        $(".passes").html(data.passes);
        $("div.progress-bar-danger").css({
            "width": fwidth
        });
        $(".fails").html(data.fails);
        $(".progress").removeClass("hidden");
        var votecount = data.passes+data.fails;
        $("#votecount").html(votecount);
    }

    function failsucc(data) {
        $(".passform button, .failform button").removeClass("process");
        $("#vinst").remove();
        $("button.vote.fail").addClass("selected").prop("disabled", true);
        $("button.vote.pass").removeClass("selected").prop("disabled", false);
        $("[rel='failtip']").tooltip('show');
        $("[rel='passtip']").tooltip('hide');
        $(".writerev").removeClass('hidden');
        $("#review_form").removeClass("hidden");
        $(".badge.points").html(data.points);
        var swidth = ((data.passes) / (data.passes + data.fails)) * 100 + "%";
        var fwidth = ((data.fails) / (data.passes + data.fails)) * 100 + "%";
        var prog = swidth / 100;
        $("div.progress-bar-success").css({
            "width": swidth
        });
        $(".passes").html(data.passes);
        $("div.progress-bar-danger").css({
            "width": fwidth
        });
        $(".fails").html(data.fails);
        $(".progress").removeClass("hidden");
        var votecount = data.passes+data.fails;
        $("#votecount").html(votecount);
    }

    function revsucc(data) {
        var r = '<div id="review-' + data.reviewid + '" class="review" itemprop="review" itemscope itemtype="http://schema.org/Review"><div class="owner_menu delrev"><form id="del_review-' + data.reviewid + '" action="/r/' + data.reviewid + '/delete" method="post"><button data-toggle="tooltip" data-placement="bottom" title="Delete" class="rdelbutton" id="' + data.reviewid + '"><i class="fa fa-trash"></i></button></form></div><span class="small author"><i class="fa fa-user"></i>&nbsp;&nbsp;<a itemprop="author" href="/profile/'+ data.user +'">'+ data.user +'</a></span><br>' + data.review + '<div class="review_meta small pull-right clearfix"><meta itemprop="datePublished" content=""> <span class="small pub_date">Just Now</span></div></div>';
        var revid = "#review-"+data.reviewid
        $(".reviews").append(r);
        $("h4.noreviews").remove();
        $('html, body').animate({
                scrollTop: $('#'+data.reviewid).offset().top - 100
            },
            'slow'
        );
        $(revid).on( "revent", function(event, revid) {
          $(".target").removeClass("target");
          $(revid).addClass("target");
          return false;
        });
        $(revid).trigger( "revent", revid);
        $(".badge.points").html(data.points);
        $('body').tooltip({selector: '.rdelbutton'});
    }
    function errorfunc(xhr, testStatus, error) {
        if (xhr.status == 429) {
            var error_text = "You're doing that too much, wait one minute before doing that again.";
            swal({   title: "Stahp!",   text: error_text,   type: "error",   confirmButtonText: "Ok" });
        }
        else if (xhr.status == 401) {
            var error_text = "You're not allowed to do this. Please sign up or login";
            swal({   title: "Stahp!",   text: error_text,   type: "error",   confirmButtonText: "Ok" });
        }
        else if (xhr.status == 406) {
            var error_text = "You need to write something between 1 - 240 characters";
            swal({   title: "Slow down...",   text: error_text,   type: "warning",   confirmButtonText: "Ok" });
        }
        else if (xhr.status == 0) {
            var error_text = "It looks like you have been disconnected from the internet. Sad.";
            swal({   title: "Internet gone?",   text: error_text,   type: "error",   confirmButtonText: "Ok" });
        }
        else {
            var error_text = xhr.status+" - "+error;
            swal({   title: "Error!",   text: error_text,   type: "error",   confirmButtonText: "Ok" });
        }
        $('button.vote').removeClass("process");
        $('.rdelbutton').removeClass("rotating");
    }
    
    $('#vote_formpass').ajaxForm({
        // dataType identifies the expected content type of the server response 
        dataType: 'json',
        success: passsucc,
        error: errorfunc
    });

    $('#vote_formfail').ajaxForm({
        dataType: 'json',
        success: failsucc,
        error: errorfunc
    });

    $('#review_form').ajaxForm({
        // dataType identifies the expected content type of the server response 
        dataType: 'json',
        clearForm: true,
        success: revsucc,
        error: errorfunc
    });
    $(".passform button, .failform button").mouseup(function() {
        $(this).addClass("process");
    });

    $(".reviews").on('click', '.rdelbutton', function(e) {
        e.preventDefault();
        var id = $(this).attr('id');
        $(this).addClass('rotating');
        //alert(id);
        $.ajax({
            url: "/r/" + id + "/delete",
            type: 'POST',
            success: function(data) {
                var revdiv = "#review-" + id;
                $(revdiv).remove();
                $(".badge.points").html(data.points);
            },
            error: errorfunc
        });
    });
    $("#reload").click(function(){
        $("#reviews").load(location.href+" #reviews>*", function(){
            $('html, body').animate({
                scrollTop: $(document).height() - $(window).height()
            },
            140,
            "easeOutQuint"
            );
        });
    });
});
//smooth scrolling
$(document).ready(function(){
    $('a[href^="#"]').on('click',function (e) {
        e.preventDefault();

        var target = this.hash;
        var $target = $(target);

        $('html, body').stop().animate({
            'scrollTop': $target.offset().top
        }, 900, 'swing');
    });
});