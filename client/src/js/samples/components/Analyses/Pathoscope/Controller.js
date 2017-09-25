import React from "react";
import { assign, xor, sortBy, sum, filter } from "lodash";
import { Icon, Flex, FlexItem, Button, Checkbox } from "virtool/js/components/Base";
import { Row, Col, Dropdown, MenuItem, FormGroup, InputGroup, FormControl } from "react-bootstrap";

import PathoscopeList from "./List";

export default class PathoscopeController extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            filterViruses: true,
            filterIsolates: true,

            findTerm: "",

            sortKey: "coverage",
            sortDescending: true,

            showReads: false,
            expanded: []
        };
    }

    static propTypes = {
        data: React.PropTypes.array,
        maxReadLength: React.PropTypes.number
    };

    collapseAll = () => this.setState({expanded: []});

    toggleIn = (virusId) => {
        this.setState({
            expanded: xor(this.state.expanded, [virusId])
        });
    };

    toggleShowReads = () => {
        this.setState({
            showReads: !this.state.showReads
        });
    };

    setSortKey = (event) => {
        this.setState({sortKey: event.target.value});
    };

    toggleSortDescending = () => {
        this.setState({sortDescending: !this.state.sortDescending});
    };

    filter = (eventKey) => {

        if (eventKey === "viruses") {
            return this.setState({filterViruses: !this.state.filterViruses});
        }

        if (eventKey === "isolates") {
            return this.setState({filterIsolates: !this.state.filterIsolates});
        }

        const filterValue = !(this.state.filterViruses && this.state.filterIsolates);

        return this.setState({
            filterViruses: filterValue,
            filterIsolates: filterValue
        });
    };

    render () {

        let data = sortBy(this.props.data, this.state.sortKey);

        if (this.state.filterViruses) {
            const totalReadsMapped = sum(data.map(v => v.reads));

            const re = this.state.findTerm ? new RegExp(this.state.findTerm, "i"): null;

            data = filter(data, (virus) => (
                (virus.pi * totalReadsMapped >= virus.length * 0.8 / this.props.maxReadLength) &&
                (!re || (re.test(virus.abbreviation) || re.test(virus.name)))
            ));
        }

        if (this.state.filterIsolates) {
            data = data.map(virus => {
                return assign({}, virus, {
                    isolates: filter(virus.isolates, isolate => isolate.pi >= 0.03 * virus.pi)
                });
            });
        }

        if (this.state.sortDescending) {
            data.reverse();
        }

        return (
            <div>
                <Row>
                    <Col xs={12} md={7}>
                        <FormGroup>
                            <InputGroup>
                                <InputGroup.Addon>
                                    <Icon name="search" />
                                </InputGroup.Addon>
                                <FormControl
                                    value={this.state.findTerm}
                                    onChange={(e) => this.setState({findTerm: e.target.value})}
                                />
                            </InputGroup>
                        </FormGroup>
                    </Col>

                    <Col xs={12} md={5}>
                        <div className="toolbar">
                            <FormGroup>
                                <InputGroup>
                                    <InputGroup.Button>
                                        <Button title="Sort Direction" onClick={this.toggleSortDescending}>
                                            <Icon name={this.state.sortDescending ? "sort-desc": "sort-asc"} />
                                        </Button>
                                    </InputGroup.Button>
                                    <FormControl
                                        componentClass="select"
                                        value={this.state.sortKey}
                                        onChange={this.setSortKey}
                                    >
                                        <option className="text-primary" value="coverage">Coverage</option>
                                        <option className="text-success" value="pi">Weight</option>
                                        <option className="text-danger" value="best">Best Hit</option>
                                    </FormControl>
                                </InputGroup>
                            </FormGroup>

                            <Button
                                icon="shrink"
                                title="Collapse"
                                onClick={this.collapseAll}
                                className="hidden-xs"
                                disabled={this.state.expanded.length === 0}
                            />

                            <Button
                                icon="pie"
                                title="Change Weight Format"
                                active={!this.state.showReads}
                                className="hidden-xs"
                                onClick={this.toggleShowReads}
                            />

                            <Dropdown id="job-clear-dropdown" onSelect={this.handleSelect} className="split-dropdown"
                                pullRight
                            >
                                <Button
                                    title="Filter"
                                    onClick={this.filter}
                                    active={this.state.filterViruses || this.state.filterIsolates}
                                >
                                    <Icon name="filter" />
                                </Button>
                                <Dropdown.Toggle />
                                <Dropdown.Menu onSelect={this.filter}>
                                    <MenuItem eventKey="viruses">
                                        <Flex>
                                            <FlexItem>
                                                <Checkbox checked={this.state.filterViruses} />
                                            </FlexItem>
                                            <FlexItem pad={5}>
                                                Viruses
                                            </FlexItem>
                                        </Flex>
                                    </MenuItem>
                                    <MenuItem eventKey="isolates">
                                        <Flex>
                                            <FlexItem>
                                                <Checkbox checked={this.state.filterIsolates} />
                                            </FlexItem>
                                            <FlexItem pad={5}>
                                                Isolates
                                            </FlexItem>
                                        </Flex>
                                    </MenuItem>
                                </Dropdown.Menu>
                            </Dropdown>
                        </div>
                    </Col>
                </Row>

                <PathoscopeList
                    data={data}
                    expanded={this.state.expanded}
                    toggleIn={this.toggleIn}
                    showReads={this.state.showReads}
                />
            </div>
        );
    }

}
