import React from "react";
import { connect } from "react-redux";
import styled from "styled-components";
import { Quality } from "../../quality/components/Quality";
import LegacyAlert from "./LegacyAlert";

const QualityLegacyAlert = styled(LegacyAlert)`
    margin-bottom: 20px;
`;

const StyledSampleQuality = styled.div`
    display: flex;
    flex-direction: column;
`;

export const SampleQuality = props => (
    <StyledSampleQuality>
        <QualityLegacyAlert />
        <Quality {...props} />
    </StyledSampleQuality>
);

const mapStateToProps = state => {
        if(state.samples.detail.quality){
            const { bases, composition, sequences } = state.samples.detail.quality;

            return {
                bases,
                composition,
                sequences
            };
        }
        else{
            return {
                bases: null,
                composition: null,
                sequences: null
            }
        }
    };


export default connect(mapStateToProps)(SampleQuality);
