import React from "react";
import styled from "styled-components";
import { connect } from "react-redux";
import { map, remove } from "lodash-es";
import { BoxGroupHeader, BoxGroup } from "../../../../base";
import { editReference } from "../../../actions";
import AddTarget from "./Add";
import EditTarget from "./Edit";
import { TargetItem } from "./Item";

const StyledAddTargets = styled(BoxGroupHeader)`
    display: flex;
    flex-direction: row;
    justify-content: space-between;
`;

const getInitialState = () => ({
    showAdd: false,
    showEdit: false
});

export const StyledAddTargetsButton = styled.a`
    cursor: pointer;
`;

export class Targets extends React.Component {
    constructor(props) {
        super(props);
        this.state = getInitialState();
    }

    handleHide = () => {
        this.setState({ showAdd: false, showEdit: false });
    };

    add = () => {
        this.setState({ showAdd: true });
    };

    edit = name => {
        this.setState({ showEdit: true, activeName: name });
    };

    handleRemove = name => {
        const targetsRemove = [...this.props.targets];
        remove(targetsRemove, { name });
        const update = {
            targets: targetsRemove
        };

        this.props.onRemove(this.props.refId, update);
    };

    render() {
        const addButton = <StyledAddTargetsButton onClick={this.add}>Add target</StyledAddTargetsButton>;

        const targetComponents = map(this.props.targets, target => (
            <TargetItem
                key={target.name}
                {...target}
                onEdit={() => this.edit(target.name)}
                onRemove={() => this.handleRemove(target.name)}
            />
        ));

        return (
            <BoxGroup>
                <StyledAddTargets>
                    <h2>Targets</h2>
                    {addButton}
                </StyledAddTargets>

                <div>{targetComponents}</div>
                <AddTarget show={this.state.showAdd} onHide={this.handleHide} />
                <EditTarget show={this.state.showEdit} onHide={this.handleHide} activeName={this.state.activeName} />
            </BoxGroup>
        );
    }
}

export const mapStateToProps = state => ({
    ...state.references.detail.targets,
    refId: state.references.detail.id,
    targets: state.references.detail.targets
});

export const mapDispatchToProps = dispatch => ({
    onRemove: (refId, update) => {
        dispatch(editReference(refId, update));
    }
});
export default connect(mapStateToProps, mapDispatchToProps)(Targets);