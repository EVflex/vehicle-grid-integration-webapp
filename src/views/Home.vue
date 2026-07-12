<template>


  <div class="container">
    <div class="row">
      <div class="col-lg-12" style="margin-bottom: 20px">
        <div class="box-main" style="border-color: #3949AB; height: 100%">
          <div class="col-lg-12 box-title" style="background-color: #C5CAE9">
            <h3>EVENT</h3>
          </div>
          <div class="center-element">
            <h1><u>E</u>lectric <u>VE</u>hicle <u>N</u>etwork analysis <u>T</u>ool</h1>
          </div>

          <div class="center-element">
            <!-- <div class="img-fluid"><img src="../assets/images/220127-icons.png" alt="Responsive image">
            </div> -->
           <img src="../assets/images/220127_icons.svg" class="img-fluid" alt="Responsive image" height: auto> 
          </div>
          
            <div class="center-element">
            
            <!-- <div class="col-lg-4 offset-4"> -->
            <div class="col-6 offset-3">
            <router-link
              class="btn btn-primary btn-block"
              style="background-color: #3949AB; border-color: #3949AB; font-size: 24px"
              :to="{ name: 'SimulateNetworkAPI' }"
              >Build a Network
            </router-link>
            </div>
          </div>

          <div class="row">
            <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/supergen.png">
            <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/turing.png">
            <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/newcastle.png">
            <img class="col-md-3 logo" style="padding-top:20px" src="../assets/logos/lrf.svg">
          </div>          

        </div>
      </div>
    </div>
  </div>

<footer class="footer mt-auto py-3">
  <div class="container text-center">
    <span class="text-muted">Copyright &copy; 2019-2022 <strong>e4futuregrid.com</strong>. All rights reserved.</span>
  </div>
</footer>

</template>
