/*
	Behaviors and animation loops for interval selector
*/

var animations = [];
var frameRate = 15, growRate = 2, shrinkRate = 1;

function processAnimations() {
	var active = false;
	for (var a in animations) {
		var anim = animations[a];
		var currentSize = jQuery(anim.element).css("font-size");
		currentSize = parseInt(currentSize.replace("px",""));
		var newSize = currentSize + (anim.finalSize < currentSize ? Math.min(-shrinkRate,currentSize - anim.finalSize) : Math.min(growRate,anim.finalSize - currentSize));
		jQuery(anim.element).css("font-size", newSize + "px");
		if (newSize == anim.finalSize) {
			animations.splice(a, 1);
		} else {
			active = true;
		}
	}
	if (active) {
		setTimeout(processAnimations, 1000/frameRate);
	}
}
function addAnimation(element, finalSize) {
	var thisIndex = jQuery(element).index();
	var found = false;
	for (var a in animations) {
		if (animations[a].index == thisIndex && jQuery(animations[a].element).is(jQuery(element))) {
			animations[a].finalSize = finalSize;
			found = true;
			break;
		}
	}
	if (!found) {
		animations.push({
			element: element,
			index: thisIndex,
			finalSize: finalSize
		});
	}
	return !found;
}

function intervalSelectMouseover() {
	if (addAnimation(this, 40)) {
		processAnimations();
	}
}

function intervalSelectMouseout() {
	var originalSize = 	jQuery(this).hasClass("distance0") ? 40 : 
						(jQuery(this).hasClass("distance1") ? 34 :
						(jQuery(this).hasClass("distance2") ? 30 :
						26));
	if (addAnimation(this, originalSize)) {
		processAnimations();
	}
}

function intervalSelectClick() {
	jQuery(this).parent().children(".intervalSelect.distance0").each(function(){
		addAnimation(this, 26);
		jQuery(this).removeClass("distance0");
	});
	jQuery(this).parent().children(".intervalSelect.distance1").each(function(){
		addAnimation(this, 26);
		jQuery(this).removeClass("distance1");
	});
	jQuery(this).parent().children(".intervalSelect.distance2").each(function(){
		addAnimation(this, 26);
		jQuery(this).removeClass("distance2");
	});
	jQuery(this).addClass("distance0")
		.each(function(){addAnimation(this,40)})
		.prev()
		.addClass("distance1")
		.each(function(){addAnimation(this,34)})
		.prev()
		.addClass("distance2")
		.each(function(){addAnimation(this,30)});
	jQuery(this)
		.next()
		.addClass("distance1")
		.each(function(){addAnimation(this,34)})
		.next()
		.addClass("distance2")
		.each(function(){addAnimation(this,30)});
	processAnimations();
}

jQuery(document).ready(function(){
	jQuery(".intervalSelect").mouseover(intervalSelectMouseover);
	jQuery(".intervalSelect").mouseout(intervalSelectMouseout);
	jQuery(".intervalSelect").click(intervalSelectClick);
});