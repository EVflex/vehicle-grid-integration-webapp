<template>

  <div class="container">
    <div class="row">
      <div class="col-lg-12">
        <div class="box-main" style="border-color: #F4511E">
          <div class="col-lg-12 box-title" style="background-color: #FFCCBC">
            <h3>About</h3>
          </div>
          <div class="col-lg-12">
            <p>This work is a collaboration of Newcastle University, Research Engineering at The Alan Turing Institute and the Supergen Energy Networks Hub.</p>
            <p>The work is funded by the e4Future grant (104227) - under UK Research and Innovation by the Department for Business, Energy and Industrial Strategy (BEIS) and The Office for Zero Emission Vehicles (OZEV) and delivered through Innovate UK; and a grant from the Lloyd's Register Foundation (G0095) under the Data-Centric Engineering Programme of The Alan Turing Institute.</p>
          </div>
          <div class="col-lg-12">
            <p>Contact <a href="https://www.turing.ac.uk/people/researchers/myriam-neaimeh">Myriam Neaimeh</a> (<a href="mailto:mneaimeh@turing.ac.uk">mneaimeh@turing.ac.uk</a>) for further details about the project.</p>
          </div>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-lg-12">
        <div class="box-main" style="border-color: #F57C00">
          <div class="col-lg-12 box-title" style="background-color: #FFE0B2">
            <h3>The EVENT simulation platform</h3>
          </div>
          <div class="col-lg-12">
            <p> The EVENT simulation platform was built by members of the Alan Turing Institute's <a href="https://www.turing.ac.uk/research-engineering">Research Engineering Group</a> in collaboration with Myriam Neaimeh.
                The network models and simulation code were developed by <a href="https://www.turing.ac.uk/people/research-associates/matthew-deakin">Matt Deakin</a> (<a href="mailto:mdeakin@turing.ac.uk">mdeakin@turing.ac.uk</a>).
            </p>
            <p>
                The website itself is built using Vue.js and Bootstrap, and FastAPI is used for the API.
                All resources are hosted on Microsoft Azure.
                <br>
                <github-link text="Website and simulation code" link="https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private"/>
                <br>
                <github-link text="API documentation" :link="fastapi_docs_url" icon="bi-lightning-fill"/>
            </p>
            <p>
                Two further GitHub repositories hold the networks used in the simulations and scripts to generate profiles in csv format from open data sources.
                <br>
                <github-link text="Network models" link="https://github.com/alan-turing-institute/vehicle-grid-integration-opendss-networks"/>
                <br>
                <github-link text="Open profiles data" link="https://github.com/alan-turing-institute/e4Future-opendata"/>
            </p>
            
          </div>
        </div>
      </div>
    </div>
    <div class="row">
      <div class="col-lg-12">
        <div class="box-main" style="border-color: #FFA000">
          <div class="col-lg-12 box-title" style="background-color: #FFECB3">
            <h3>Further resources</h3>
          </div>
          <div class="col-lg-12">
            <p>For information about the wider project, see <a href="https://www.turing.ac.uk/research/research-projects/vehicle-grid-integration">the project website</a>.</p>
            <br>
            <p>
            <github-link icon="bi-book-fill" text="Hybrid European MV-LV Network Models for Smart Distribution Network Modelling." link="http://arxiv.org/abs/2009.14240"/>
            <br>
            <github-link icon="bi-book-fill" text="A probabilistic approach to combining smart meter and electric vehicle charging data to investigate distribution network impacts." link="https://www.sciencedirect.com/science/article/pii/S0306261915001944"/>
           </p>
          </div>
        </div>
      </div>
    </div>
  </div>

</template>

<script>
import GithubLink from "../components/GithubLink.vue"
    export default {
        components: { GithubLink },
        data() {
            return { "fastapi_docs_url": new URL("/docs", process.env.VUE_APP_API_URL).href }
        }
    }
</script>