var xmlns = "http://www.w3.org/2000/svg",
  xlinkns = "http://www.w3.org/1999/xlink",
  select = function(s) {
    return document.querySelector(s);
  },
  selectAll = function(s) {
    return document.querySelectorAll(s);
  },
    heroMessageArr = ["launching^creative ideas", "building^the future", "Another^message here"],
    heroLine0 = select('.heroLine0'),
    heroLine1 = select('.heroLine1'),
    display = select('.display'),
    display = select('.display'),
    rocketSVG = select('.rocketSVG'),
    smokeTail = select('.smokeTail'),
    rocketGroup = select('.rocketGroup'),
    rocketBody = select('.rocketBody'),
    rocketFlameContainer = select('.rocketFlameContainer'),
    rocketFlame = select('.rocketFlame'),
    stageWidth = 1280,
    stageHeight = 630,
    numStars = 100,
    star = select('.star'),
    cloudGroup = select('.cloudGroup'),
    allClouds = selectAll('.cloudGroup circle'),
    starContainer = select('.starContainer'),
    starTl = new TimelineMax().timeScale(1),
    rocketFlameTl,
    cloudsTl = new TimelineMax().timeScale(1),
    message0Str = "buildStars();",
    message1Str = "buildRocketClouds();",
    message2Str = "launchRocket();",
    heroMessageCount = 0,
    numHeroMessages = heroMessageArr.length,
    displayInitPos = {x:720, y:445},
    rocketGroupInitPos = {x:580, y:415},
    cloudGroupInitPos = {x:190, y:645},
     mainTl = new TimelineMax({repeat:0, paused:true}),
    attractContainer = select('.attractContainer'),
    allAttractCircles = selectAll('.attractContainer circle'),
    readoutTl = new TimelineMax({paused:true}),
    attractDelay = 2,
    attractTl = new TimelineMax({paused:true, repeat:-1})


TweenMax.set('svg', {
  visibility: 'visible'
})

TweenMax.set(rocketGroup, {
 x:rocketGroupInitPos.x,
 y:rocketGroupInitPos.y
})
TweenMax.set(cloudGroup, {
 x:cloudGroupInitPos.x,
 y:cloudGroupInitPos.y
})
TweenMax.set(display, {
 x:displayInitPos.x,
 y:displayInitPos.y
})
TweenMax.set('circle', {
 transformOrigin:'50% 50%'
})

TweenMax.set(display, {
 transformOrigin:'0% 85%',
 scale:0,
 rotation:-23
})

TweenMax.set([rocketFlame, rocketFlameContainer, smokeTail], {
 transformOrigin:'50% 0%'
})
TweenMax.set([rocketFlameContainer, smokeTail], {
 scale:0
})

attractTl.staggerFromTo(allAttractCircles, 1.6, {
 scale:0,
 alpha:1,
 cycle:{

 strokeWidth:[30,20, 15,5],
 }
},{
 scale:1.2,
 alpha:0,
 strokeWidth:0,
 repeat:-1,
 repeatDelay:attractDelay,
 ease:Sine.easeOut
},0.25)

function initMessage(){
 TweenMax.staggerTo([heroLine0, heroLine1], 1, {
  cycle:{
   text:function(i){
    return heroMessageArr[heroMessageCount].split('^')[i]
   }
  },
  ease:Linear.easeNone,
 },1, function(){
   attractTl.play();
     })
 //heroLine0.textContent = ()
 //heroLine1.textContent = (heroMessageArr[heroMessageCount].split('^')[1])

}

function createStars(){

 var starClone, tl;
 for(var i = 0; i < numStars; i++){
  starClone = star.cloneNode(true);
  starContainer.appendChild(starClone);
  TweenMax.set(starClone, {
   attr:{
    cx:randomBetween(0, stageWidth),
    cy:randomBetween(0, stageHeight),
    r:randomBetween(5, 20)/10
   }
  })

  tl = new TimelineMax();
  tl.from(starClone, randomBetween(10, 30)/10, {
   alpha:0.03,
   //fill:'#000',
   repeat:-1,
   yoyo:true,
   repeatDelay:randomBetween(10, 40)/10,
   ease:Linear.easeNone
  })

  //starTl.add(tl, 0);

 }

}

function createClouds(){
 var tl, origin = "", cx, cy;
 for(var i = 0;  i < allClouds.length; i++){

  TweenMax.set(allClouds[i%10], {
   fill:'#B2E0E3'
  })
 TweenMax.set(allClouds[i%30], {
   fill:'#C1E7E9'
  })

 TweenMax.set(allClouds[i%4], {
   fill:'#B2E0E3'
  })

  tl = new TimelineMax();
  tl.fromTo(allClouds[i], randomBetween(2, 6)/10, {
   scale:1.2
  },{
   scale:2,
   repeat:-1,
   yoyo:true,
   ease:Sine.easeOut
  })

  cloudsTl.add(tl, i/140)
 }

 cloudsTl.pause();

}

function flameFlicker(){

 rocketFlameTl = new TimelineMax()//.timeScale(2);
 rocketFlameTl.fromTo(rocketFlame, 0.1, {
  scale:0.9
 },{
  scale:0.7,
  repeat:-1,
  yoyo:true,
  ease:Linear.easeNone

 })

}

function changeHeroMessage(){
 heroMessageCount++
 heroMessageCount = (heroMessageCount >= numHeroMessages) ? 0 : heroMessageCount;
 var splitMessage = heroMessageArr[heroMessageCount].split('^');

 heroLine0.textContent = splitMessage[0];
 heroLine1.textContent = splitMessage[1];
 //console.log(splitMessage);
}

function resetAll(){

 TweenMax.set(allClouds, {
  //scale:1
 })

 readoutTl.timeScale(1);
 //readoutTl.pause(0);
 //console.log(cloudsTl)
 //cloudsTl.seek(0);
 //rocketFlameTl.seek(0);
 rocketFlameTl.restart(true, false);
//cloudsTl.progress(0)
 cloudsTl.restart(true, false);

 cloudsTl.pause();

}

function createReadoutText(){

 readoutTl.to('.line0', 2, {
   text:message0Str,
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = message0Str
   },
   onReverseComplete:function(){
     this.target[0].textContent = '';
    this.seek(0);
   }
  })

  .to('.line1', 3, {
   text:message1Str,
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = message1Str
   },
   onReverseComplete:function(){
     this.target[0].textContent = '';
    this.seek(0);
   }
  },'+=1')
  .to('.line2', 3, {
   text:message2Str,
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = message2Str
   },
   onReverseComplete:function(){
     this.target[0].textContent = '';
    this.seek(0);
   }
  },'+=1')


}

function createMainTl(){


  mainTl.to(attractContainer, 0.6, {
   alpha:0
  })
 .to(display, 1, {
   scaleX:1,
   ease:Elastic.easeOut.config(0.7, 0.5)
  },'-=0')
.to(display, 0.8, {
   scaleY:1,
   rotation:0,
   ease:Elastic.easeOut.config(0.9, 0.85)
  },'-=1')
   .fromTo(readoutTl, readoutTl.duration(),{
   time:0
  },{
   time:readoutTl.duration(),
   ease:Linear.easeNone,
   onComplete:function(){readoutTl.pause()}
  })
   .to(smokeTail, 1, {
   scale:1,
   ease:Power3.easeIn
  })
   .to(rocketFlameContainer, 1, {
     scale:1,
   ease:Power3.easeIn
    },'-=1')
  .addCallback(function(){cloudsTl.play(); rocketFlameTl.play()})

   .staggerTo([cloudGroup, rocketGroup], 10, {
   cycle:{

   y:['-=1350','-=1200'],
   },
   ease:Sine.easeIn
  },'+=2')
  .set(display, {
   //autoAlpha:0
  },'-=5')
  .addCallback(changeHeroMessage, '-=4')


  .staggerFromTo([cloudGroup, rocketGroup], 1,{
   cycle:{
    y:[cloudGroupInitPos.y+200, rocketGroupInitPos.y+200]
   }
  },{
   cycle:{
    //x:[cloudGroupInitPos.x, rocketGroupInitPos.x],
    y:[cloudGroupInitPos.y, rocketGroupInitPos.y]
   },
   immediateRender:false
  },0,'+=3')
 .to([rocketFlameContainer, smokeTail], 1, {
   scale:0
  })
 .addCallback(function(){readoutTl.timeScale(6); readoutTl.reverse(); }, '-=5')
 .to(display, 0.4, {
   alpha:0,
   rotation:23,
   ease:Back.easeIn.config(0.3)
  },'-=2')
.to(attractContainer,1, {
   alpha:1
  })
 /* .to(readoutTl, readoutTl.duration(),{
   time:0,
   ease:Linear.easeNone
  }) */


/*.to('.line2',2, {
   text:"             ",
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = ""
   }
  },'-=5')
.to('.line1',2, {
   text:"             ",
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = ""
   }
  })
.to('.line0',1, {
   text:"        ",
   ease:Linear.easeNone,
   onUpdate:function(){
     this.target[0].textContent += '_'
   },
   onComplete:function(){
     this.target[0].textContent = ""
   }
  })
  */
mainTl.timeScale(2)


}

function launch(){

 //console.log(mainTl.isActive())
 resetAll();

 if(!mainTl.isActive()){
   mainTl.restart();
 }

}


//ScrubGSAPTimeline(mainTl);
//tl.seek(0)



function randomBetween(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min);
}
initMessage();
createStars();
createClouds();
flameFlicker();
createReadoutText();
createMainTl();
rocketSVG.onclick = launch;