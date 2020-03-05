import React, { Component } from 'react';

// local imports
import { Divider, Dropdown, Form, Input, Label, Button, Segment } from 'semantic-ui-react'

import '../css/App.css';

class App extends Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.logout = this.logout.bind(this);
    this.clearError = this.clearError.bind(this);
    this.clearMessage = this.clearMessage.bind(this);
    this.create = this.create.bind(this);

    this.state = {
      apiToken: "",
      auth: false,
      images: [],
      regions: [],
      droplets: [],
      headers: {},
      message: "",
      error: ""
    };
  } 
   
  async componentDidMount() {
    const apiToken = localStorage.getItem("do-api:token")
    if (apiToken) {
      await this.auth(apiToken)
      await this.fetchResources()
      await this.fetchClasses()
    }
  }

  async logout() {
    this.setState({apiToken:null, auth: false})
    localStorage.removeItem("do-api:token") 
  }

  async fetchClasses() {
    try {
      const resources = await fetch("/api/v1/classes/", {
        headers: this.state.headers,
        method: "GET",
      })
      const json = await resources.json()
      this.setState({"classes":json})
    } catch(error) {
      this.setState({"error":`${error}`})
    }
  }

  async fetchResources() {
    try {
      const resources = await fetch("/api/v1/resources/", {
        headers: this.state.headers,
        method: "GET",
        
      })
      const json = await resources.json()
      this.setState({"images":json['images']})
      this.setState({"regions":json['regions']})
    } catch(error) {
      this.setState({"error":`${error}`})
    }
  }

  async create() {
    const token = localStorage.getItem("do-api:token")
    try {
      const resources = await fetch("/api/v1/droplets/create/", {
        headers: this.state.headers,
        method: "POST",
        body: JSON.stringify({"name": this.name, "region": this.region, "image": this.image}),
      })
      const json = await resources.json()
    } catch(error) {
      this.setState({error: `${error}`, message: ""})
    }
  }

  async auth(token) {
    const headers = {
      "Authorization": `Token ${token}`,
      "Content-Type": "application/json"
    }
    try {
      const authenticated = await fetch("/api/v1/auth/check/", {
        headers: headers,
        method: "GET"
      })
      const message = await authenticated.json()
      if (authenticated.status === 200) {
        this.setState({
          apiToken: token,
          auth: true,
          headers: headers,
          message: `${message.message}`
        })
        localStorage.setItem("do-api:token", token)
        this.fetchResources()
      } else {
        this.setState({error: `${message.detail}`})
      }
    } catch(error) {
      this.setState({error: `${error}`})
    }
  }

  async clearError() {
    this.setState({"error": null})
  }

  async clearMessage() {
    this.setState({"message": null})
  }

  async handleChange(e, value) {
    if (this.state.image && this.state.region && this.state.dropletName) {
      this.setState({submitVisible: true})
    }
    if (value.id === 'region') {
      this.setState({region: value.value})
    }
    if (value.id === 'image') {
      this.setState({image: value.value})
    }
    if (e.target.id === 'dropletName') {
      this.setState({dropletName: e.target.value})
    }
    if (e.target.id === 'apiToken') {
      if (e.target.value.length >= 40) {
        await this.auth(e.target.value)
      }
    }
  }

  render() {
    const {message, error, auth, images, regions, image, region, classes } = this.state;
    const keyedRegions = regions.map(region => ({
      key: region.slug,
      value: region.slug,
      text: region.name
    }))
    const keyedImages = images.map(image => ({
      key: image.slug,
      value: image.slug,
      text: `${image.distribution} - ${image.slug}`
    }))
      return (
      <div className="App">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/semantic-ui@2.4.2/dist/semantic.min.css"></link>
        
        {error && <Segment
          id='error'
          floated='right'
          inverted
          color='red'
          onClick={this.clearError}
          >
          {error}
        </Segment>}

        {message && <Segment
          id='message'
          floated='right'
          inverted
          color='green'
          onClick={this.clearMessage}
          >
          {message}
        </Segment>}

        {auth && <Button
          id="logout"
          onClick={this.logout}
          basic color='teal'
          >
            Logout
        </Button>}

        {!auth && <header as='h1' className="App-header">
          DigitalOcean Workshop & Class API
          <Divider />
          <Form>
            <Form.Field>
              <Input
                id="apiToken"
                type="text"
                size="massive"
                icon="key"
                placeholder="a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
                onChange={this.handleChange}
                //value={apiToken}
              />
              <Label pointing>Enter your API token to get started</Label>
            </Form.Field>
          </Form>
        </header> }
        {auth && <div className="App-main">
          <Form>
            <Form.Field>
              <Input
                id="dropletName"
                type="text"
                size="massive"
                icon="write"
                placeholder="tor01 development droplet"
                onChange={this.handleChange}
              />
              <Label pointing>Choose a descriptive name for your droplet</Label>
            </Form.Field>
          </Form>
          <Divider />
          <Dropdown
            id="region"
            placeholder='Select a region for your droplet'
            size="massive"
            icon="globe"
            selection
            clearable
            onChange={this.handleChange}
            options={keyedRegions}
            value={region}
          />
          <Divider />
          <Dropdown
            id="image"
            placeholder='Select an operating system for your droplet'
            size="massive"
            icon="disk"
            selection
            clearable
            onChange={this.handleChange}
            options={keyedImages}
            value={image}
          />
          <Divider />
          {this.state.image && this.state.region && this.state.dropletName && 
            <Button
              id="create"
              name={this.state.dropletName}
              region={this.state.region}
              image={this.state.image}
              onClick={this.create}
              size='massive'
              color='green'>Create Droplet!</Button>
          }
        </div> }
      </div>
    );
  }
}

export default App;
