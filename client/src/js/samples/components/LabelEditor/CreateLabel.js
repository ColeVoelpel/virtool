import React from "react";
import { connect } from "react-redux";
import { InputGroup, InputLabel, Input, Button, InputError, Modal, ModalHeader, ModalBody } from "../../../base";
import { ColorSelector } from "./ColorSelector";

const getInitialState = ({ labelName, color, description, errorName, errorColor }) => ({
    labelName: labelName || "",
    color: color || "",
    description: description || "",
    errorName: errorName || "",
    errorColor: errorColor || ""
});

export class CreateLabel extends React.Component {
    constructor(props) {
        super(props);
        this.state = getInitialState(this.props);
    }

    handleChange = e => {
        const { name, value } = e.target;
        this.setState({
            [name]: value,
            error: ""
        });
    };

    handleColorSelection = e => {
        this.setState(e);
    };

    handleSubmit = () => {
        if (this.state.labelName === "") {
            this.setState({ errorName: "Please enter a label name" });
        } else if (this.state.color === "") {
            this.setState({ errorColor: "Please select a color" });
        } else {
            this.props.submitNewLabel({
                name: this.state.labelName,
                description: this.state.description,
                color: this.state.color
            });
        }
    };

    render() {
        const labelName = this.state.labelName;
        const description = this.state.description;
        const color = this.state.color;
        const errorName = this.state.errorName;
        const errorColor = this.state.errorColor;
        return (
            <Modal label="Create Label" show={this.props.show} onHide={this.props.onHide}>
                <ModalHeader>Create a label</ModalHeader>
                <ModalBody>
                    <form>
                        <InputGroup>
                            <InputLabel>Name</InputLabel>
                            <Input
                                placeholder="Label name"
                                name="labelName"
                                value={labelName}
                                onChange={this.handleChange}
                                error={errorName}
                            ></Input>
                            <InputError>{errorName}</InputError>
                            <InputLabel>Description</InputLabel>
                            <Input
                                placeholder="Description"
                                name="description"
                                value={description}
                                onChange={this.handleChange}
                            ></Input>
                        </InputGroup>
                        <ColorSelector
                            name="color"
                            color={color}
                            errorColor={errorColor}
                            onColorChange={this.handleColorSelection}
                        ></ColorSelector>
                        <Button color="green" onClick={this.handleSubmit}>
                            Create
                        </Button>
                    </form>
                </ModalBody>
            </Modal>
        );
    }
}
export const mapStateToProps = state => ({
    show: get(state.router.location.state, "labelCreate", false)
});

export const mapDispatchToProps = dispatch => ({
    onHide: () => {
        dispatch(pushState({ labelCreate: false }));
    }
});

export default connect(mapStateToProps, mapDispatchToProps)(CreateLabel);
